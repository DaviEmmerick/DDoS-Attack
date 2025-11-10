from fastapi import FastAPI
import time
import uvicorn

app = FastAPI()

@app.get("/api/data")
async def get_data():
    try:
        # Fica paralisado por 10ms para simular uma operação
        time.sleep(0.01) 
    except Exception as e:
        # Apenas para garantir que o servidor não quebre
        print(f"Erro no sleep: {e}")
        
    return {"message": "API está funcionando!"}

if __name__ == "__main__":
    """
    Permite rodar o arquivo diretamente com 'python target/main.py',
    embora o recomendado seja 'uvicorn target.main:app --port 8001'
    """
    uvicorn.run(app, host="0.0.0.0", port=8001)