from flask import Flask, render_template, request
import httpx
import asyncio
import threading
import time

app = Flask(__name__)

simulation_status = {
    'unprotected': 'Pronto',
    'protected': 'Pronto'
}

async def send_request(session, url):
    try:
        await session.get(url, timeout=5)
        return "success"
    except httpx.ReadTimeout:
        return "timeout"
    except httpx.ConnectError:
        return "connect_error"
    except Exception:
        return "other_error"

async def run_attack_async(url, num_requests, concurrency, target_key):
    global simulation_status
    print(f"[{target_key.upper()}] Iniciando simulação em {url}...")
    print(f"[{target_key.upper()}] Total de Requisições: {num_requests}")
    print(f"[{target_key.upper()}] Concorrência: {concurrency}")
    simulation_status[target_key] = f"Rodando... (0/{num_requests})"
    
    start_time = time.time()
    results = {"success": 0, "timeout": 0, "connect_error": 0, "other_error": 0, "rate_limited": 0}
    
    semaphore = asyncio.Semaphore(concurrency)
    tasks = []

    async def concurrent_task(session, url):
        async with semaphore:
            result = await send_request(session, url)
            return result

    async with httpx.AsyncClient(http2=True) as session: 
        for i in range(num_requests):
            task = asyncio.create_task(concurrent_task(session, url))
            tasks.append(task)
            
            if (i + 1) % 100 == 0:
                simulation_status[target_key] = f"Rodando... ({i+1}/{num_requests})"

        responses = await asyncio.gather(*tasks)
        
        for r in responses:
            results[r] += 1

    end_time = time.time()
    
    print(f"--- [{target_key.upper()}] Simulação Concluída ---")
    print(f"Total de {num_requests} requisições disparadas.")
    print(f"Tempo total: {end_time - start_time:.2f} segundos.")
    print(f"Resultados: {results}")
    simulation_status[target_key] = f"Concluído em {end_time - start_time:.2f}s. (Resultados: {results})"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start-attack', methods=['POST'])
def start_attack_route():
    """Inicia a simulação em um endpoint (protegido ou não)."""
    data = request.json
    target = data.get('target') 
    
    if target == 'unprotected':
        target_url = "http://127.0.0.1:8001/api/data"
        target_key = 'unprotected'
    elif target == 'protected':
        target_url = "http://127.0.0.1:8002/api/data-protected"
        target_key = 'protected'
    else:
        return "Alvo inválido", 400

    try:
        total_requests = int(data.get('requests', 10000))
        concurrency_limit = int(data.get('concurrency', 500))
    except ValueError:
        return "Parâmetros 'requests' e 'concurrency' devem ser números inteiros.", 400

    print(f"[FLASK] Recebida ordem para iniciar a simulação em '{target_key}'.")
    
    def run_in_thread():
        try:
            asyncio.run(run_attack_async(target_url, total_requests, concurrency_limit, target_key))
        except Exception as e:
            print(f"Erro na thread de simulação: {e}")
            global simulation_status
            simulation_status[target_key] = f"Erro: {e}"
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    
    return f"Simulação iniciada para '{target_key}'! Verifique o console do 'flask' para o progresso."

@app.route('/status')
def get_status():
    return simulation_status

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# run: uvicorn api-with-limiting:app --port 8002