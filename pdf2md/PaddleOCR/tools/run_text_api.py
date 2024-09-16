from infer import ocr_title_text
import fastapi
import os, pathlib

global text_sys

app = fastapi.FastAPI()

@app.on_event("startup")
def load_model():
    global text_sys
    text_sys = ocr_title_text.load_model()
    
@app.post("/infer/text")
def infer_text(file: bytes = fastapi.File(...)):
    global text_sys
    try:
        res = ocr_title_text.infer(file, text_sys, is_text=True)
        return { 'status': 'success', 'result': res }
    except Exception as e:
        return { 'status': 'error', 'error': str(e) }
    
@app.post("/infer/title")
def infer_title(file: bytes = fastapi.File(...)):
    global text_sys
    try:
        res = ocr_title_text.infer(file, text_sys, is_title=True)
        return { 'status': 'success', 'result': "## " + res }
    except Exception as e:
        return { 'status': 'error', 'error': str(e) }


if __name__ == '__main__':
    os.chdir(pathlib.Path(__file__).resolve().parent.parent)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=20002)