import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, List, Optional

sys.path.append(str(Path(__file__).parent.parent))

from src.config import DRAFT_FORMAT
from src.models.draft_state_simple import DraftState
from src.services.dan_draft_parser import DanDraftParser
from src.services.sheet_parser import SheetParser

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SheetsProvider(ABC):
    """Abstract base class for Google Sheets providers"""

    @abstractmethod
    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Read data from a sheet range"""
        pass


class GoogleSheetsProvider(SheetsProvider):
    """Real Google Sheets provider using Google Sheets API"""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(
        self, credentials_file: Optional[str] = None, token_file: Optional[str] = None
    ):
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API dependencies not available. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        # Use absolute paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        default_creds = project_root / "credentials.json"
        default_token = project_root / "token.json"

        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CREDENTIALS_FILE", str(default_creds)
        )
        self.token_file = token_file or os.getenv(
            "GOOGLE_TOKEN_FILE", str(default_token)
        )
        self.service = None
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def _get_service(self):
        """Get authenticated Google Sheets service"""
        if self.service:
            return self.service

        def _auth():
            creds = None

            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(
                    self.token_file, self.SCOPES
                )

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Google credentials file not found: {self.credentials_file}"
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())

            return build("sheets", "v4", credentials=creds)

        # Run authentication in thread pool to avoid blocking
        self.service = await asyncio.get_event_loop().run_in_executor(
            self.executor, _auth
        )
        return self.service

    async def read_range(self, sheet_id: str, range_name: str) -> List[List[Any]]:
        """Read data from Google Sheets"""
        try:
            service = await self._get_service()

            def _read():
                result = (
                    service.spreadsheets()
                    .values()
                    .get(spreadsheetId=sheet_id, range=range_name)
                    .execute()
                )
                return result.get("values", [])

            # Execute API call in thread pool
            values = await asyncio.get_event_loop().run_in_executor(
                self.executor, _read
            )
            logger.info(
                f"Successfully read {len(values)} rows from sheet {sheet_id}, range {range_name}"
            )
            return values

        except Exception as e:
            logger.error(f"Error reading from Google Sheets: {str(e)}")
            raise


def get_parser(format_type: str = None) -> SheetParser:
    """Factory function to get the appropriate parser for the draft format.

    Args:
        format_type: Draft format type ('dan' or 'adam'). Uses config if not specified.

    Returns:
        SheetParser instance for the specified format

    Raises:
        ValueError: If format_type is not supported
    """
    if format_type is None:
        format_type = DRAFT_FORMAT

    if format_type == "dan":
        return DanDraftParser()
    else:
        raise ValueError(
            f"Unsupported draft format: {format_type}. Supported formats: dan"
        )


class SheetsService:
    """Service for interacting with Google Sheets"""

    def __init__(
        self,
        provider: SheetsProvider,
        use_cache: bool = True,
    ):
        self.provider = provider
        # Cache simplified - draft_cache was removed in refactoring
        self.cache = None

    # Legacy methods removed - parsing logic moved to format-specific parsers

    async def read_draft_data(
        self, sheet_id: str, range_name: str, force_refresh: bool = False
    ) -> DraftState:
        """Read and parse draft data from sheets using format-specific parser."""
        try:
            # Get the appropriate parser for the configured format
            parser = get_parser()

            logger.info(f"Reading draft data for {sheet_id} range {range_name}")

            # Fetch sheet data from Google Sheets
            data = await self.provider.read_range(sheet_id, range_name)

            # Use the parser to convert sheet data to DraftState
            draft_state = await parser.parse_draft_data(data)

            logger.info(
                f"Successfully parsed {len(draft_state.picks)} picks for {len(draft_state.teams)} teams"
            )

            return draft_state

        except Exception as e:
            # Import ParseError here to avoid circular imports
            from src.services.sheet_parser import ParseError

            if isinstance(e, ParseError):
                # For format/parsing errors, return empty state with warning
                logger.warning(
                    f"Draft data parsing failed: {str(e)}. Returning empty draft state."
                )
                return DraftState(picks=[], teams=[])
            else:
                # For other errors (network, auth, etc.), re-raise
                logger.error(f"Error reading draft data: {str(e)}")
                raise
