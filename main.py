from fastapi import FastAPI
from pydantic import BaseModel
import pymupdf4llm
import fitz
import httpx

app = FastAPI()

class ExtractionRequest(BaseModel):
        file_url: str
        file_name: str

class ExtractionResponse(BaseModel):
        success: bool
        content: str = ""
        page_count: int = 0
        method: str = "pymupdf4llm"
        error: str = ""
        fallback_required: bool = False

@app.get("/health")
def health():
        return {"status": "ok", "version": "2.0-pymupdf4llm"}

@app.post("/extract", response_model=ExtractionResponse)
async def extract(req: ExtractionRequest):
        try:
                    async with httpx.AsyncClient(timeout=60) as client:
                                    resp = await client.get(req.file_url)
                                    if resp.status_code != 200:
                                                        return ExtractionResponse(
                                                                                success=False,
                                                                                fallback_required=True,
                                                                                error=f"Download failed: {resp.status_code}"
                                                        )
                                                    pdf_bytes = resp.content

                    doc = fitz.open(
                        stream=pdf_bytes,
                        filetype="pdf"
                    )
                    page_count = len(doc)

            try:
                            md_text = pymupdf4llm.to_markdown(
                                                doc,
                                                show_progress=False
                            )
                            content = md_text
                            method = "pymupdf4llm"
except Exception:
            pages = []
            for page_num in range(page_count):
                                page = doc[page_num]
                                text = page.get_text("text")
                                if text.strip():
                                                        pages.append(text.strip())
                                                content = "\n\n".join(pages)
            method = "pymupdf-plaintext"

        doc.close()

        content = content.replace("\x00", "")

        if len(content.strip()) < 100:
                        return ExtractionResponse(
                                            success=False,
                                            fallback_required=True,
                                            error="Too little text — may be scanned PDF"
                        )

        return ExtractionResponse(
                        success=True,
                        content=content,
                        page_count=page_count,
                        method=method
        )

except Exception as e:
        return ExtractionResponse(
                        success=False,
                        fallback_required=True,
                        error=str(e)
        )
