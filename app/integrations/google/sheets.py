import os
import asyncio
import json
from typing import List, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import settings
from app.schemas.analytics import CompanyStats
from app.core.logging import logger

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsProvider:
    """
    Reporting layer for exporting analytics to Google Sheets.
    Uses batchUpdate to minimize API calls and handle rate limits.
    """
    def __init__(self):
        self.spreadsheet_id = settings.GOOGLE_SPREADSHEET_ID
        self.creds_file = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None)
        self.service = None
        
        json_creds = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if not self.spreadsheet_id or (not self.creds_file and not json_creds):
            logger.warning("Google credentials not found. Google Sheets integration is disabled.")
            return
            
        try:
            if json_creds:
                creds_dict = json.loads(json_creds)
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            else:
                creds = Credentials.from_service_account_file(self.creds_file, scopes=SCOPES)
            self.service = build('sheets', 'v4', credentials=creds)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {str(e)}")

    def _is_configured(self) -> bool:
        return bool(self.service and self.spreadsheet_id)

    async def publish_statistics(self, stats: CompanyStats) -> None:
        """
        Publishes the aggregated statistics to the configured Google Spreadsheet.
        Does not block or crash the application if Google API is unavailable.
        """
        if not self._is_configured():
            logger.debug("Skipping Google Sheets publish: not configured")
            return
            
        # Format Dashboard Data
        dashboard_values = [
            ["Показатель", "Значение"],
            ["Всего монтажей", stats.total_installations],
            ["Всего заказов с переносами", stats.installations_with_postponement],
            ["Всего переносов (фактов)", stats.total_postponements],
            ["% переносов", f"{stats.postponement_rate:.2f}%"],
            ["Лучший сотрудник", stats.best_employee.employee_name if stats.best_employee else "Нет данных"],
            ["Наихудший показатель", stats.worst_employee.employee_name if stats.worst_employee else "Нет данных"]
        ]

        # Format Employees Data
        employees_values = [
            [
                "Монтажник", "Монтажей", "Заказов с переносами", "Всего переносов",
                "1 перенос", "2 переноса", "3+ переноса", "% переносов", 
                "Среднее", "Вина монтажника", "Клиент", "Техника", 
                "Диспетчер", "Другие", "Рейтинг"
            ]
        ]
        
        for e in stats.employees:
            employees_values.append([
                e.employee_name,
                e.total_installations,
                e.installations_with_postponement,
                e.total_postponements,
                e.one_postponement,
                e.two_postponements,
                e.three_plus_postponements,
                f"{e.postponement_rate:.2f}%",
                f"{e.average_postponements:.2f}",
                e.reasons_breakdown.get("employee_fault", 0),
                e.reasons_breakdown.get("client_request", 0),
                e.reasons_breakdown.get("technical", 0),
                e.reasons_breakdown.get("dispatcher_error", 0),
                e.reasons_breakdown.get("other", 0) + e.reasons_breakdown.get("materials", 0) + e.reasons_breakdown.get("weather", 0) + e.reasons_breakdown.get("force_majeure", 0),
                e.rank if e.rank else "-"
            ])

        # Atomically update multiple ranges
        data = [
            {"range": "Dashboard!A1:B10", "values": dashboard_values},
            {"range": "Employees!A1:O1000", "values": employees_values}
        ]
        
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": data
        }
        
        def _execute_update():
            return self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id, 
                body=body
            ).execute()
        
        try:
            # Run the blocking Google API call in a thread pool to keep async loop free
            await asyncio.to_thread(_execute_update)
            logger.info("Successfully published statistics to Google Sheets")
        except Exception as e:
            # Fallback handled safely: PostgreSQL already has the data.
            # Next retry/sync run will attempt to update it again.
            logger.error(f"Failed to publish to Google Sheets API: {str(e)}")

    async def append_postponement_log(self, ticket_number: str, employee_name: str, tg_id: str, reason: str, date_str: str) -> None:
        """
        Appends a single row to a log sheet when a new postponement is detected from chat.
        """
        if not self._is_configured():
            return
            
        values = [[date_str, ticket_number, employee_name, tg_id, reason]]
        
        body = {
            "values": values
        }
        
        def _execute_append():
            return self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id, 
                range="Логи!A1:E",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
        try:
            await asyncio.to_thread(_execute_append)
            logger.info(f"Appended log for ticket {ticket_number} to Google Sheets")
        except Exception as e:
            logger.error(f"Failed to append log to Google Sheets API: {str(e)}")

    async def async_initialize(self) -> None:
        """
        Ensures the 'Логи' sheet exists and has the correct headers.
        """
        if not self._is_configured():
            return
            
        def _execute_init():
            # 1. Get spreadsheet info
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_titles = [s['properties']['title'] for s in sheets]
            
            # 2. If 'Логи' doesn't exist, create or rename it
            if 'Логи' not in sheet_titles:
                target_sheet = next((s for s in sheets if s['properties']['title'] in ['Лист1', 'Sheet1']), None)
                if target_sheet:
                    rename_request = {
                        "requests": [{
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": target_sheet['properties']['sheetId'],
                                    "title": "Логи"
                                },
                                "fields": "title"
                            }
                        }]
                    }
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body=rename_request
                    ).execute()
                    logger.info("Renamed default sheet to 'Логи'.")
                else:
                    add_sheet_request = {
                        "requests": [{"addSheet": {"properties": {"title": "Логи"}}}]
                    }
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body=add_sheet_request
                    ).execute()
                    logger.info("Created 'Логи' sheet in Google Spreadsheet.")
                
            # Create Dashboard and Employees if they don't exist
            if 'Dashboard' not in sheet_titles:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": [{"addSheet": {"properties": {"title": "Dashboard"}}}]}
                ).execute()
            if 'Employees' not in sheet_titles:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": [{"addSheet": {"properties": {"title": "Employees"}}}]}
                ).execute()
                
            # 3. Write headers to row 1
            headers = [["Дата", "Заявка", "Монтажник", "TG ID", "Причина"]]
            body = {"values": headers}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Логи!A1:E1",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
        try:
            await asyncio.to_thread(_execute_init)
            logger.info("Verified Google Sheets initialization (Headers set).")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {str(e)}")
