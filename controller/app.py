from flask import Flask, render_template, request, jsonify
from flask_cors import CORS 
import httpx
import asyncio
import threading
import time

app = Flask(__name__, template_folder='templates') 
CORS(app) 

simulation_status = {
    'unprotected': 'Pronto',
    'protected': 'Pronto'
}

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(simulation_status)

async def send_request(session, url, stats):
    try:
        response = await session.get(url, timeout=5)
        if 200 <= response.status_code < 300:
            stats['success'] += 1
        elif response.status_code == 429: 
            stats['rate_limited'] += 1
        else:
            stats['failed'] += 1
    except Exception:
        stats['errors'] += 1

async def run_attack_async(url, num_requests, concurrency, target_key):
    """Roda a simulação assíncrona e atualiza o status global."""
    
    print(f"[ATAQUE EM {target_key.upper()}] Iniciando simulação em {url}...")
    simulation_status[target_key] = 'Rodando: 0%'
    
    stats = {'success': 0, 'rate_limited': 0, 'failed': 0, 'errors': 0}
    start_time = time.time()
    
    tasks = []
    try:
        async with httpx.AsyncClient() as session:
            for i in range(num_requests):
                task = asyncio.ensure_future(send_request(session, url, stats))
                tasks.append(task)
                
                if i % 100 == 0 or i == num_requests - 1: 
                    percent = (i + 1) * 100 / num_requests
                    simulation_status[target_key] = f'Rodando: {percent:.0f}%'
                
                if len(tasks) >= concurrency:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    tasks = [t for t in tasks if not t.done()]
            
            if tasks:
                await asyncio.gather(*tasks)

    except Exception as e:
        print(f"[ERRO NO ATAQUE {target_key.upper()}] {e}")
        simulation_status[target_key] = f'Erro: {e}'
        return

    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"--- Simulação {target_key.upper()} Concluída ---")
    print(f"Total de {num_requests} requisições enviadas.")
    print(f"Tempo total: {total_time:.2f} segundos.")
    print(f"Resultados: {stats}")
    
    simulation_status[target_key] = f'Concluído! (Sucesso: {stats["success"]}, Rate Limit: {stats["rate_limited"]})'


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start-attack', methods=['POST'])
def start_attack_route():
    """Inicia uma simulação de ataque em uma thread separada."""
    data = request.json
    
    target = data.get('target') # 'unprotected' ou 'protected'
    total_requests = data.get('requests', 10000)
    concurrency_limit = data.get('concurrency', 500)
    
    if target == 'unprotected':
        target_url = "http://127.0.0.1:8001/api/data"
        target_key = 'unprotected'
    elif target == 'protected':
        target_url = "http://127.0.0.1:8002/api/data"
        target_key = 'protected'
    else:
        return jsonify({"error": "Alvo inválido"}), 400

    if simulation_status[target_key].startswith('Rodando'):
        return jsonify({"message": f"Simulação em {target_key} já está em progresso."}), 429

    print(f"[FLASK] Recebida ordem para simulação em {target_key}...")

    def run_in_thread():
        """Wrapper para rodar o loop asyncio em uma thread."""
        try:
            asyncio.run(run_attack_async(target_url, total_requests, concurrency_limit, target_key))
        except Exception as e:
            print(f"Erro na thread {target_key}: {e}")
            simulation_status[target_key] = f'Erro na thread'
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    
    simulation_status[target_key] = 'Iniciando...'
    return jsonify({"message": f"Simulação iniciada em {target_key}! Verifique o console."})

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# run: flask run --port 5000 