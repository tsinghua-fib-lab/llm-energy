import ocr_formula
import fastapi

global model, tokenizer

app = fastapi.FastAPI()

@app.on_event('startup')
def load_model():
    global model, tokenizer
    model, tokenizer = ocr_formula.load_model(None, True, 'cuda')

@app.post('/infer')
def infer(file: bytes = fastapi.File(...)):
    global model, tokenizer
    try:
        res = ocr_formula.infer(file, model, tokenizer, 'cuda')
        return {'status': 'success', 'result': f"$$\n{res}\n$$" }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=20000)