from flask import Flask, request, jsonify
from flask_cors import CORS
from costamar_v4_2_FINAL_VERIFICADO import buscar_vuelos

app = Flask(__name__)
CORS(app)

CIUDADES_A_IATA = {
    'lima': 'LIM', 'cusco': 'CUZ', 'cuzco': 'CUZ',
    'arequipa': 'AQP', 'iquitos': 'IQT', 'piura': 'PIU',
    'trujillo': 'TRU', 'chiclayo': 'CIX', 'tacna': 'TCQ',
    'puno': 'JUL', 'juliaca': 'JUL'
}

def obtener_codigo_iata(ciudad):
    ciudad_limpia = ciudad.split(',')[0].strip().lower()
    return CIUDADES_A_IATA.get(ciudad_limpia)

@app.route('/api/cotizar', methods=['POST'])
def cotizar_vuelo():
    try:
        data = request.get_json()
        origen = data.get('origen', '')
        destino = data.get('destino', '')
        fecha_ida = data.get('fechaIda', '')
        adultos = int(data.get('adultos', 1))
        
        codigo_origen = obtener_codigo_iata(origen)
        codigo_destino = obtener_codigo_iata(destino)
        
        if not codigo_origen or not codigo_destino:
            return jsonify({'success': False, 'error': 'Ciudad no encontrada'}), 400
        
        print(f"\n🔍 Buscando: {codigo_origen} → {codigo_destino} ({adultos} pasajeros)")
        
        vuelos = buscar_vuelos(
            origen=codigo_origen,
            destino=codigo_destino,
            fecha_ida=fecha_ida,
            fecha_vuelta=None,
            adultos=adultos,
            ninos=0,
            infantes=0,
            top=None
        )
        
        if not vuelos:
            return jsonify({'success': False, 'error': 'No se encontraron vuelos'})
        
        print(f"✅ {len(vuelos)} vuelos encontrados")
        
        return jsonify({'success': True, 'vuelos': vuelos})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 API COSTAMAR INICIADA")
    print("="*60)
    print("📡 URL: http://localhost:5000")
    print("✅ Endpoints:")
    print("   • POST /api/cotizar")
    print("   • GET  /api/health")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
