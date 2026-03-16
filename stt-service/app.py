from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import uvicorn
import tempfile
import os

MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
DEVICE = os.getenv("STT_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")

app = FastAPI(title="STT Service", version="1.0.0")

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
)


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Expected audio file")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        segments, _ = model.transcribe(tmp_path, language="ru")
        text_parts = [segment.text.strip() for segment in segments if segment.text]
        text = " ".join(text_parts).strip()

        if not text:
            raise HTTPException(status_code=422, detail="Empty transcription")

        return JSONResponse({"text": text})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

