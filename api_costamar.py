from flask import Flask, request, jsonify
from flask_cors import CORS
from costamar_v4_2_FINAL_VERIFICADO import buscar_vuelos
import hashlib, time as _time
 
_cache = {}
CACHE_TTL = 300  # 5 minutos
 
def cache_get(key):
    if key in _cache:
        data, ts = _cache[key]
        if _time.time() - ts < CACHE_TTL:
            return data
    return None
 
def cache_set(key, data):
    _cache[key] = (data, _time.time())
 
app = Flask(__name__)
CORS(app)
 
CIUDADES_A_IATA = {
    # Perú
    'lima': 'LIM', 'cusco': 'CUZ', 'cuzco': 'CUZ',
    'arequipa': 'AQP', 'iquitos': 'IQT', 'piura': 'PIU',
    'trujillo': 'TRU', 'chiclayo': 'CIX', 'tacna': 'TCQ',
    'puno': 'JUL', 'juliaca': 'JUL', 'tarapoto': 'TPP',
    'pucallpa': 'PCL', 'tumbes': 'TBP', 'puerto maldonado': 'PEM',
    'ayacucho': 'AYP', 'cajamarca': 'CJA', 'huanuco': 'HUU',
    'jaén': 'JAE', 'talara': 'TYL',
    # Sudamérica
    'bogotá': 'BOG', 'bogota': 'BOG', 'medellín': 'MDE', 'medellin': 'MDE',
    'cali': 'CLO', 'cartagena': 'CTG', 'barranquilla': 'BAQ',
    'santiago': 'SCL', 'buenos aires': 'EZE',
    'córdoba': 'COR', 'cordoba': 'COR', 'mendoza': 'MDZ',
    'rosario': 'ROS', 'salta': 'SLA', 'tucumán': 'TUC',
    'bariloche': 'BRC', 'ushuaia': 'USH',
    'quito': 'UIO', 'guayaquil': 'GYE',
    'são paulo': 'GRU', 'sao paulo': 'GRU', 'rio de janeiro': 'GIG',
    'brasilia': 'BSB', 'belo horizonte': 'CNF', 'florianopolis': 'FLN',
    'porto alegre': 'POA', 'salvador': 'SSA', 'recife': 'REC',
    'fortaleza': 'FOR', 'manaos': 'MAO',
    'montevideo': 'MVD', 'asuncion': 'ASU', 'asunción': 'ASU',
    'caracas': 'CCS', 'santa cruz': 'VVI', 'la paz': 'LPB',
    'antofagasta': 'ANF', 'concepción': 'CCP',
    'puerto montt': 'PMC', 'iquique': 'IQQ',
    # Norteamérica y Caribe
    'miami': 'MIA', 'nueva york': 'JFK', 'los ángeles': 'LAX', 'los angeles': 'LAX',
    'orlando': 'MCO', 'atlanta': 'ATL', 'houston': 'IAH',
    'fort lauderdale': 'FLL', 'newark': 'EWR',
    'ciudad de méxico': 'MEX', 'cancún': 'CUN', 'cancun': 'CUN',
    'punta cana': 'PUJ', 'san josé': 'SJO', 'san jose': 'SJO',
    'panama': 'PTY', 'panamá': 'PTY', 'curazao': 'CUR',
    'san salvador': 'SAL', 'la habana': 'HAV',
    # Europa
    'madrid': 'MAD', 'barcelona': 'BCN', 'paris': 'CDG', 'parís': 'CDG',
    'frankfurt': 'FRA', 'amsterdam': 'AMS', 'roma': 'FCO',
    'milan': 'MXP', 'london': 'LHR', 'londres': 'LHR',
}
 
def obtener_codigo_iata(ciudad):
    ciudad_limpia = ciudad.split(',')[0].strip().lower()
    return CIUDADES_A_IATA.get(ciudad_limpia)
 
@app.route('/api/cotizar', methods=['POST'])
def cotizar_vuelo():
    try:
        data = request.get_json()
        origen   = data.get('origen', '')
        destino  = data.get('destino', '')
        fecha_ida = data.get('fechaIda', '')
        fecha_ida = fecha_ida.replace('-', '')  # convierte YYYY-MM-DD → YYYYMMDD
 
        # FIX: leer ninos e infantes del request (antes quedaban fijos en 0)
        adultos  = int(data.get('adultos', 1))
        ninos    = int(data.get('ninos', 0))
        infantes = int(data.get('infantes', 0))
 
        codigo_origen  = obtener_codigo_iata(origen)
        codigo_destino = obtener_codigo_iata(destino)
 
        if not codigo_origen or not codigo_destino:
            return jsonify({'success': False, 'error': 'Ciudad no encontrada'}), 400
 
        # FIX: clave de caché incluye ninos e infantes para evitar mezclar resultados
        cache_key = hashlib.md5(
            f"{codigo_origen}{codigo_destino}{fecha_ida}{adultos}{ninos}{infantes}".encode()
        ).hexdigest()
 
        cached = cache_get(cache_key)
        if cached:
            print("⚡ Respuesta desde caché")
            return jsonify(cached)
 
        print(f"\n🔍 Buscando: {codigo_origen} → {codigo_destino} ({adultos}A {ninos}N {infantes}I)")
 
        vuelos = buscar_vuelos(
            origen=codigo_origen,
            destino=codigo_destino,
            fecha_ida=fecha_ida,
            fecha_vuelta=None,
            adultos=adultos,
            ninos=ninos,
            infantes=infantes,
            top=None
        )
 
        if not vuelos:
            return jsonify({'success': False, 'error': 'No se encontraron vuelos'})
 
        print(f"✅ {len(vuelos)} vuelos encontrados")
 
        resultado = {'success': True, 'vuelos': vuelos}
        cache_set(cache_key, resultado)
 
        return jsonify(resultado)
 
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
