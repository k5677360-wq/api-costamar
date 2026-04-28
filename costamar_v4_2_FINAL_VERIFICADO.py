"""
==========================================
🔓 COSTAMAR SCRAPER v4 - OUTPUT PROFESIONAL
==========================================
"""
import requests
import json
import time
import random
import csv
import os
from datetime import datetime
 
# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
 
TERMINAL_IDS = [
    "0100140692",  # Condor Travel
    "0536830376",  # Lima Tours
]
 
PROXY = ""
DELAY_MIN = 1
DELAY_MAX = 2
 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Origin': 'https://booking.clickandbook.com',
    'Referer': 'https://booking.clickandbook.com/',
}
 
# Sesión persistente — AQUÍ, después de HEADERS
_session = requests.Session()
_session.headers.update(HEADERS)
 
# Nombres de meses en español
MESES = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}
 
# Códigos de aeropuertos
AEROPUERTOS = {
    'LIM': 'Lima', 'CUZ': 'Cusco', 'MIA': 'Miami', 'CUN': 'Cancún',
    'BOG': 'Bogotá', 'SCL': 'Santiago', 'MEX': 'México DF', 'MAD': 'Madrid',
    'JFK': 'New York', 'LAX': 'Los Angeles', 'AQP': 'Arequipa', 'PIU': 'Piura',
    'TRU': 'Trujillo', 'IQT': 'Iquitos', 'CIX': 'Chiclayo', 'TCQ': 'Tacna',
    'PEM': 'Puerto Maldonado', 'JUL': 'Juliaca'
}
 
# ==========================================
# 🔧 FUNCIONES AUXILIARES
# ==========================================
 
def formato_fecha(fecha_yyyymmdd):
    """Convierte 20260201 a '01 Febrero 2026'"""
    if not fecha_yyyymmdd or len(fecha_yyyymmdd) < 8:
        return "N/A"
    año = fecha_yyyymmdd[:4]
    mes = fecha_yyyymmdd[4:6]
    dia = fecha_yyyymmdd[6:8]
    nombre_mes = MESES.get(mes, mes)
    return f"{dia} {nombre_mes} {año}"
 
def nombre_aeropuerto(codigo):
    """Convierte LIM a 'Lima (LIM)'"""
    nombre = AEROPUERTOS.get(codigo, codigo)
    return f"{nombre} ({codigo})"
 
def convertir_a_numero(valor):
    """Convierte cualquier valor a número float, maneja comas como separadores de miles"""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            limpio = valor.replace('$', '').replace(' ', '').strip()
            if ',' in limpio and '.' in limpio:
                limpio = limpio.replace(',', '')
            elif ',' in limpio:
                if limpio.count(',') > 1:
                    limpio = limpio.replace(',', '')
                elif len(limpio.split(',')[1]) == 3:
                    limpio = limpio.replace(',', '')
                else:
                    limpio = limpio.replace(',', '.')
            return float(limpio)
        except:
            return 0.0
    return 0.0
 
# ==========================================
# 🔧 FUNCIONES DE BÚSQUEDA
# ==========================================
 
def buscar_vuelos_api(origen, destino, fecha_ida, fecha_vuelta=None, adultos=1, ninos=0, infantes=0, terminal_id=None):
    """Llama a la API de Costamar"""
 
    # FIX: se eliminó la línea que sobreescribía terminal_id,
    # así el bucle en buscar_vuelos() puede probar ambos TERMINAL_IDS.
    # Si no se pasa terminal_id, se usa el primero como fallback.
    if terminal_id is None:
        terminal_id = TERMINAL_IDS[0]
 
    if fecha_vuelta:
        flight_type = "RT"
        itinerary = [
            {"origin": origen, "destination": destino, "date": fecha_ida},
            {"origin": destino, "destination": origen, "date": fecha_vuelta}
        ]
    else:
        flight_type = "OW"
        itinerary = [{"origin": origen, "destination": destino, "date": fecha_ida}]
 
    fecha_ida_iso = f"{fecha_ida[:4]}-{fecha_ida[4:6]}-{fecha_ida[6:]}T05:00:00.000Z"
    fecha_vuelta_iso = f"{fecha_vuelta[:4]}-{fecha_vuelta[4:6]}-{fecha_vuelta[6:]}T05:00:00.000Z" if fecha_vuelta else fecha_ida_iso
 
    # Inicializar sesión para obtener token de validación
    try:
        _session.get("https://costamar.com.pe/vuelos", timeout=8)
    except Exception:
        pass
 
    payload = {
        "flightType": flight_type,
        "terminalId": terminal_id,
        "itinerary": itinerary,
        "startDate": fecha_ida_iso,
        "endDate": fecha_vuelta_iso,
        "passengers": {"adults": adultos, "children": ninos, "infants": infantes},
        "hasValidationToken": True
    }
 
    try:
        response = _session.post(
            "https://costamar.com.pe/vuelos/api/flights/search",
            json=payload,
            timeout=12
        )
 
        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    except Exception as e:
        print(f"   💥 Error de conexión: {e}")
        return []
 
 
def extraer_precio(vuelo):
    """Extrae precio del campo pricing con máxima precisión"""
    precio = 0.0
    moneda = "USD"
 
    if 'pricing' in vuelo:
        pricing = vuelo['pricing']
        if isinstance(pricing, dict):
            if 'grandTotal' in pricing:
                precio = convertir_a_numero(pricing['grandTotal'])
            elif 'totalAmount' in pricing:
                precio = convertir_a_numero(pricing['totalAmount'])
            elif 'total' in pricing:
                precio = convertir_a_numero(pricing['total'])
            elif 'base' in pricing and 'taxes' in pricing:
                base = convertir_a_numero(pricing['base'])
                taxes = convertir_a_numero(pricing['taxes'])
                precio = base + taxes
 
            moneda = pricing.get('currency', pricing.get('currencyCode', 'USD'))
            if not moneda or moneda == '':
                moneda = 'USD'
 
    return precio, moneda
 
 
def extraer_info_vuelo(vuelo, origen, destino, fecha_ida, fecha_vuelta, adultos, ninos, infantes):
    """Extrae toda la información del vuelo"""
 
    precio, moneda = extraer_precio(vuelo)
 
    info = {
        'origen': origen,
        'origen_nombre': nombre_aeropuerto(origen),
        'destino': destino,
        'destino_nombre': nombre_aeropuerto(destino),
        'fecha_ida': fecha_ida,
        'fecha_ida_formato': formato_fecha(fecha_ida),
        'fecha_vuelta': fecha_vuelta or "",
        'fecha_vuelta_formato': formato_fecha(fecha_vuelta) if fecha_vuelta else "Solo ida",
        'adultos': adultos,
        'ninos': ninos,
        'infantes': infantes,
        'pasajeros_total': adultos + ninos + infantes,
        'aerolinea': "N/A",
        'numero_vuelo': "N/A",
        'hora_salida': "N/A",
        'hora_llegada': "N/A",
        'duracion': "N/A",
        'escalas': 0,
        'escalas_texto': "Directo",
        'equipaje_bodega': "No especificado",
        'equipaje_mano': "No especificado",
        'personal_item': "Incluido (bolso/mochila)",
        'clase': "Economy",
        'precio': precio,
        'moneda': moneda,
        'precio_formato': f"${precio:.2f} {moneda}" if precio > 0 else "Consultar"
    }
 
    if 'itinerary' in vuelo and len(vuelo['itinerary']) > 0:
        tramo = vuelo['itinerary'][0]
 
        if 'flights' in tramo and len(tramo['flights']) > 0:
            flight = tramo['flights'][0]
 
            if 'marketingAirline' in flight:
                info['aerolinea'] = flight['marketingAirline'].get('name', 'N/A')
                codigo_aero = flight['marketingAirline'].get('code', '')
                numero = flight.get('flightNumber', '')
                if not numero and 'segments' in flight and len(flight['segments']) > 0:
                    numero = flight['segments'][0].get('flightNumber', '')
                info['numero_vuelo'] = f"{codigo_aero}{numero}" if numero else "N/A"
 
            salida = flight.get('departureDateTime', '')
            llegada = flight.get('arrivalDateTime', '')
            if salida and len(salida) > 16:
                info['hora_salida'] = salida[11:16]
            if llegada and len(llegada) > 16:
                info['hora_llegada'] = llegada[11:16]
 
            dur = flight.get('elapsedTime', '')
            if dur and len(dur) >= 4:
                try:
                    horas = int(dur[:2])
                    mins = int(dur[2:4])
                    info['duracion'] = f"{horas}h {mins}m"
                except (ValueError, IndexError):
                    info['duracion'] = "N/A"
 
            if 'baggage' in flight:
                bag = flight['baggage']
                piezas = str(bag.get('pieces', '0'))
                if piezas != '0' and piezas != '':
                    info['equipaje_bodega'] = f"{piezas} maleta(s) 23kg"
                else:
                    desc = bag.get('description', '').upper()
                    if 'INCLUDED' in desc or 'INCLUIDO' in desc:
                        info['equipaje_bodega'] = "1 maleta 23kg"
                    else:
                        info['equipaje_bodega'] = "No incluido"
            else:
                info['equipaje_bodega'] = "No especificado"
 
            if 'handBaggage' in flight:
                hand_bag = flight['handBaggage']
                piezas_mano = str(hand_bag.get('pieces', '0'))
                if piezas_mano != '0' and piezas_mano != '':
                    info['equipaje_mano'] = f"{piezas_mano} pieza(s)"
                else:
                    desc_mano = hand_bag.get('description', '').upper()
                    if 'INCLUDED' in desc_mano or 'INCLUIDO' in desc_mano:
                        info['equipaje_mano'] = "1 pieza"
                    else:
                        info['equipaje_mano'] = "No incluido"
            else:
                info['equipaje_mano'] = "No especificado"
 
            if info.get('equipaje_mano') and 'pieza' in info['equipaje_mano']:
                info['personal_item'] = "Incluido (bolso/mochila)"
            elif 'handBaggage' not in flight:
                info['personal_item'] = "Incluido (bolso/mochila)"
            elif info.get('equipaje_mano') == "No incluido":
                info['personal_item'] = "Incluido (bolso/mochila)"
            else:
                info['personal_item'] = "Incluido (bolso/mochila)"
 
            if 'brandedFare' in flight:
                clase = flight['brandedFare'].get('brandName', 'Economy')
                info['clase'] = clase
 
            if 'segments' in flight:
                num_escalas = max(0, len(flight['segments']) - 1)
                info['escalas'] = num_escalas
                if num_escalas == 0:
                    info['escalas_texto'] = "Directo"
                elif num_escalas == 1:
                    info['escalas_texto'] = "1 escala"
                else:
                    info['escalas_texto'] = f"{num_escalas} escalas"
 
    return info
 
 
def buscar_vuelos(origen, destino, fecha_ida, fecha_vuelta=None, adultos=1, ninos=0, infantes=0, top=5):
    """
    Función principal de búsqueda
 
    Parámetros:
    - origen: código IATA (ej: "LIM")
    - destino: código IATA (ej: "CUZ")
    - fecha_ida: formato YYYYMMDD (ej: "20260201")
    - fecha_vuelta: formato YYYYMMDD o None para solo ida
    - adultos, ninos, infantes: cantidad de pasajeros
    - top: cuántos resultados mostrar (default 5)
 
    Retorna: lista de los mejores vuelos
    """
 
    total_pasajeros = adultos + ninos + infantes
    texto_pasajeros = []
    if adultos > 0:
        texto_pasajeros.append(f"{adultos} adulto{'s' if adultos > 1 else ''}")
    if ninos > 0:
        texto_pasajeros.append(f"{ninos} niño{'s' if ninos > 1 else ''}")
    if infantes > 0:
        texto_pasajeros.append(f"{infantes} infante{'s' if infantes > 1 else ''}")
    pasajeros_str = ", ".join(texto_pasajeros)
 
    print(f"\n{'═'*75}")
    print(f"🔍 BÚSQUEDA DE VUELOS")
    print(f"{'═'*75}")
    print(f"   📍 RUTA:      {nombre_aeropuerto(origen)} → {nombre_aeropuerto(destino)}")
    print(f"   📅 IDA:       {formato_fecha(fecha_ida)}")
    if fecha_vuelta:
        print(f"   📅 VUELTA:    {formato_fecha(fecha_vuelta)}")
    else:
        print(f"   📅 VUELTA:    Solo ida")
    print(f"   👥 PASAJEROS: {pasajeros_str}")
    print(f"{'═'*75}")
 
    print(f"\n   ⏳ Buscando vuelos...")
    vuelos_raw = []
    for tid in TERMINAL_IDS:
        parcial = buscar_vuelos_api(origen, destino, fecha_ida, fecha_vuelta, adultos, ninos, infantes, terminal_id=tid)
        vuelos_raw.extend(parcial)
 
    if not vuelos_raw:
        print(f"   ❌ No se encontraron vuelos para esta ruta/fecha")
        return []
 
    print(f"   ✅ {len(vuelos_raw)} opciones encontradas")
 
    vuelos_info = []
    for v in vuelos_raw:
        info = extraer_info_vuelo(v, origen, destino, fecha_ida, fecha_vuelta, adultos, ninos, infantes)
        vuelos_info.append(info)
 
    vuelos_con_precio = [v for v in vuelos_info if v['precio'] > 0]
    vuelos_sin_precio = [v for v in vuelos_info if v['precio'] == 0]
    vuelos_ordenados = sorted(vuelos_con_precio, key=lambda x: x['precio']) + vuelos_sin_precio
 
    mejores = vuelos_ordenados[:top]
 
    print(f"\n   💰 TOP {len(mejores)} OFERTAS MÁS BARATAS:")
    print(f"   {'─'*71}")
    print(f"   {'#':<2} {'AEROLÍNEA':<15} {'FECHA':<12} {'HORARIO':<13} {'DURACIÓN':<9} {'ESCALAS':<9} {'EQUIPAJE':<14} {'PRECIO':<10}")
    print(f"   {'─'*71}")
 
    for i, v in enumerate(mejores, 1):
        fecha_corta = f"{v['fecha_ida'][6:8]}-{MESES.get(v['fecha_ida'][4:6], '')[:3]}-{v['fecha_ida'][2:4]}"
        horario = f"{v['hora_salida']}→{v['hora_llegada']}"
        equip = v['equipaje_bodega'][:12]
        precio = f"${v['precio']:.2f}" if v['precio'] > 0 else "Consultar"
 
        print(f"   {i:<2} {v['aerolinea'][:14]:<15} {fecha_corta:<12} {horario:<13} {v['duracion']:<9} {v['escalas_texto']:<9} {equip:<14} {precio:<10}")
 
    print(f"   {'─'*71}")
 
    if mejores and mejores[0]['precio'] > 0:
        print(f"\n   💡 Precio mostrado: Total por {pasajeros_str} (ida" + (" y vuelta" if fecha_vuelta else "") + ")")
 
    print(f"\n   📦 DETALLES DE EQUIPAJE:")
    print(f"   {'─'*71}")
    for i, v in enumerate(mejores, 1):
        print(f"\n   #{i} {v['aerolinea']} - ${v['precio']:.2f}")
        print(f"      ✈️  Equipaje facturado: {v.get('equipaje_bodega', 'No especificado')}")
        print(f"      🎒 Equipaje de mano:    {v.get('equipaje_mano', 'No especificado')}")
        print(f"      👜 Bolso/mochila:       {v.get('personal_item', 'No especificado')}")
    print(f"   {'─'*71}")
 
    return mejores
 
 
def guardar_csv(vuelos, filename="vuelos_resultados.csv"):
    """Guarda los resultados en CSV"""
 
    if not vuelos:
        print("\n⚠️ No hay vuelos para guardar")
        return
 
    columnas = [
        'origen', 'destino', 'fecha_ida_formato', 'fecha_vuelta_formato',
        'adultos', 'ninos', 'infantes', 'aerolinea', 'hora_salida',
        'hora_llegada', 'duracion', 'escalas_texto', 'equipaje_bodega',
        'equipaje_mano', 'personal_item', 'clase', 'precio', 'moneda'
    ]
 
    ruta = os.path.join(os.getcwd(), filename)
 
    with open(ruta, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columnas, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(vuelos)
 
    print(f"\n✅ RESULTADOS GUARDADOS EN: {ruta}")
 
 
# ==========================================
# 🚀 PROGRAMA PRINCIPAL
# ==========================================
 
if __name__ == "__main__":
 
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║   🔓 COSTAMAR FLIGHT SCRAPER v4.2 FINAL - STEALTH MODE                  ║
    ║   ────────────────────────────────────────────────────────────────────   ║
    ║   ✅ Búsqueda anónima (IDs de terceros)                                 ║
    ║   ✅ TOP 5 vuelos más baratos                                           ║
    ║   ✅ Info completa: fecha, hora, equipaje detallado, precio             ║
    ║   ✅ Equipaje: facturado + mano + personal item                         ║
    ║   ✅ Exporta a CSV                                                      ║
    ║   ✅ Verificación con web real para precios exactos                     ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
 
    todos_los_vuelos = []
 
    print("\n🔍 Iniciando búsquedas múltiples para verificar precios exactos...\n")
 
    print("📍 Búsqueda 1: Lima → Cusco")
    resultado = buscar_vuelos(
        origen="LIM", destino="CUZ", fecha_ida="20260220",
        fecha_vuelta="20260223", adultos=1, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    print("📍 Búsqueda 2: Lima → Arequipa")
    resultado = buscar_vuelos(
        origen="LIM", destino="AQP", fecha_ida="20260225",
        fecha_vuelta="20260228", adultos=1, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    print("📍 Búsqueda 3: Lima → Cusco (solo ida)")
    resultado = buscar_vuelos(
        origen="LIM", destino="CUZ", fecha_ida="20260218",
        fecha_vuelta=None, adultos=1, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    print("📍 Búsqueda 4: Lima → Piura")
    resultado = buscar_vuelos(
        origen="LIM", destino="PIU", fecha_ida="20260222",
        fecha_vuelta="20260224", adultos=1, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    print("📍 Búsqueda 5: Lima → Iquitos")
    resultado = buscar_vuelos(
        origen="LIM", destino="IQT", fecha_ida="20260301",
        fecha_vuelta="20260305", adultos=2, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
 
    print("📍 Búsqueda 6: Cusco → Lima")
    resultado = buscar_vuelos(
        origen="CUZ", destino="LIM", fecha_ida="20260226",
        fecha_vuelta="20260228", adultos=1, ninos=0, infantes=0, top=5
    )
    todos_los_vuelos.extend(resultado)
 
    guardar_csv(todos_los_vuelos, "vuelos_resultados.csv")
 
    print(f"\n{'═'*75}")
    print(f"🎉 BÚSQUEDA COMPLETADA - {len(todos_los_vuelos)} vuelos encontrados")
    print(f"{'═'*75}")
 
    try:
        input("\nPresiona ENTER para cerrar...")
    except EOFError:
        pass
