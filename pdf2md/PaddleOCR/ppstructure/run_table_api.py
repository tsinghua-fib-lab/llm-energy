from table import ocr_table
import fastapi
import os, pathlib

global table_sys

app = fastapi.FastAPI()

@app.on_event("startup")
def load_model():
    global table_sys
    table_sys = ocr_table.load_model()
    
@app.post("/infer")
def infer(file: bytes = fastapi.File(...)):
    global table_sys
    try:
        res = ocr_table.infer(file, table_sys)
        return { 'status': 'success', 'result': res }
    except Exception as e:
        return { 'status': 'error', 'error': str(e) }
    
if __name__ == '__main__':
    os.chdir(pathlib.Path(__file__).resolve().parent)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=20001)