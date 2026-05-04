"""
AI-powered company document parser using Claude.
Ported from documentParser.ts — extracts directors, shareholders,
incorporation date, license numbers, and business address from raw document text.
"""
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

from .anthropic_client import messages_create_json_object

DOCUMENT_TYPES = (
    "MOA", "AOA", "business_license",
    "registration_certificate", "incorporation_document", "other"
)

TYPE_INSTRUCTIONS: dict[str, str] = {
    "MOA": "This is a Memorandum of Association. Extract company structure, objectives, and governance details.",
    "AOA": "This is Articles of Association. Extract governance rules, director powers, and shareholder rights.",
    "business_license": "This is a business license. Extract license number, expiry date, and business scope.",
    "registration_certificate": "This is a company registration certificate. Extract registration number, incorporation date, and company details.",
    "incorporation_document": "This is an incorporation document. Extract all company formation and registration details.",
    "other": "This is a company document. Extract all available company information.",
}

SYSTEM_PROMPT = """You are an expert document parser specializing in extracting company information from legal and regulatory documents.
Extract all relevant information accurately and return ONLY a JSON object with this exact structure:
{
  "companyName": "string or null",
  "registrationNumber": "string or null",
  "incorporationDate": "YYYY-MM-DD or null",
  "businessAddress": "string or null",
  "directorNames": ["name1", "name2"],
  "directorAddresses": ["addr1", "addr2"],
  "shareholderInfo": {"name": "percentage"},
  "businessType": "string or null",
  "licenseNumber": "string or null",
  "licenseExpiryDate": "YYYY-MM-DD or null",
  "confidence": 0-100
}
Be thorough but only include information explicitly stated in the document."""


async def parse_company_document(
    document_text: str,
    document_type: str = "other",
) -> dict:
    """
    Call Claude to extract structured company data from document text.
    Returns ParsedDocumentData dict with confidence score.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    instructions = TYPE_INSTRUCTIONS.get(document_type, TYPE_INSTRUCTIONS["other"])
    prompt = f"{instructions}\n\nDocument Content:\n{document_text}\n\nExtract all company information and provide a confidence score (0-100)."

    parsed = await messages_create_json_object(
        api_key=ANTHROPIC_API_KEY,
        model=ANTHROPIC_MODEL,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        timeout_s=45.0,
    )
    return {
        "company_name":       parsed.get("companyName"),
        "registration_number": parsed.get("registrationNumber"),
        "incorporation_date": parsed.get("incorporationDate"),
        "business_address":   parsed.get("businessAddress"),
        "director_names":     parsed.get("directorNames") or [],
        "director_addresses": parsed.get("directorAddresses") or [],
        "shareholder_info":   parsed.get("shareholderInfo") or {},
        "business_type":      parsed.get("businessType"),
        "license_number":     parsed.get("licenseNumber"),
        "license_expiry_date": parsed.get("licenseExpiryDate"),
        "confidence":         parsed.get("confidence", 0),
    }


async def extract_text_from_file(file_bytes: bytes, mime_type: str) -> str:
    """
    Extract plain text from PDF or image file.
    PDF  → pdfplumber (pip install pdfplumber)
    Image → pytesseract (pip install pytesseract pillow)
    Falls back gracefully if libraries are not installed.
    """
    if mime_type == "application/pdf":
        try:
            import pdfplumber
            import io
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n".join(text_parts)
        except ImportError:
            return "[PDF extraction unavailable — pip install pdfplumber]"
        except Exception as e:
            return f"[PDF extraction error: {e}]"

    if mime_type.startswith("image/"):
        try:
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img)
        except ImportError:
            return "[OCR unavailable — pip install pytesseract pillow]"
        except Exception as e:
            return f"[OCR error: {e}]"

    # Plain text / fallback
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def validate_extracted_data(data: dict) -> bool:
    """Return True if confidence >= 50 and at least one key field is present."""
    if data.get("confidence", 0) < 50:
        return False
    return any([
        data.get("company_name"),
        data.get("registration_number"),
        data.get("incorporation_date"),
        data.get("business_address"),
    ])
