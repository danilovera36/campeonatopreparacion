from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from functools import wraps
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from collections import defaultdict

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta')

# Configuración de la aplicación
class Config:
    USUARIO_ADMIN = os.getenv('ADMIN_USER', 'dvera')
    CONTRASENA_ADMIN = os.getenv('ADMIN_PASS', 'danilo22')
    DATA_FILE = "preparacion_liga_rosarina.json"
    BACKUP_DIR = "backups"
    MAX_GOLEADORES = 10
    EQUIPOS = [
        "ESTUDIANTES EL COLLA",
        "ROSARIO ATLETICO",
        "EL PARQUE",
        "PEÑAROL",
        "REFORMERS",
        "INDEPENDIENTE"
    ]

# --- FIXTURE PREDEFINIDO ---
FIXTURE = [
    # Fecha 1
    [
        {"local": "PEÑAROL", "visitante": "REFORMERS"},
        {"local": "INDEPENDIENTE", "visitante": "ROSARIO ATLETICO"},
        {"local": "EL PARQUE", "visitante": "ESTUDIANTES EL COLLA"},
    ],
    # Fecha 2
    [
        {"local": "INDEPENDIENTE", "visitante": "REFORMERS"},
        {"local": "PEÑAROL", "visitante": "EL PARQUE"},
        {"local": "ROSARIO ATLETICO", "visitante": "ESTUDIANTES EL COLLA"},
    ],
    # Fecha 3
    [
        {"local": "REFORMERS", "visitante": "EL PARQUE"},
        {"local": "ESTUDIANTES EL COLLA", "visitante": "INDEPENDIENTE"},
        {"local": "ROSARIO ATLETICO", "visitante": "PEÑAROL"},
    ],
    # Fecha 4
    [
        {"local": "REFORMERS", "visitante": "ESTUDIANTES EL COLLA"},
        {"local": "INDEPENDIENTE", "visitante": "PEÑAROL"},
        {"local": "EL PARQUE", "visitante": "ROSARIO ATLETICO"},
    ],
    # Fecha 5
    [
        {"local": "REFORMERS", "visitante": "ROSARIO ATLETICO"},
        {"local": "INDEPENDIENTE", "visitante": "EL PARQUE"},
        {"local": "PEÑAROL", "visitante": "ESTUDIANTES EL COLLA"},
    ]
]

def backup_data():
    """Crea un backup de los datos actuales"""
    if not os.path.exists(Config.BACKUP_DIR):
        os.makedirs(Config.BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(Config.BACKUP_DIR, f"backup_{timestamp}.json")
    
    try:
        with open(Config.DATA_FILE, "r", encoding="utf-8") as source:
            with open(backup_file, "w", encoding="utf-8") as target:
                target.write(source.read())
        logging.info(f"Backup creado: {backup_file}")
    except Exception as e:
        logging.error(f"Error creando backup: {str(e)}")

def escudo_equipo(nombre_equipo):
    mapping = {
        "ESTUDIANTES EL COLLA": "CEEC.png",
        "EL PARQUE": "elparque.png",
        "INDEPENDIENTE": "independiente.png",
        "PEÑAROL": "peñarol.png",
        "REFORMERS": "reformers.png",
        "ROSARIO ATLETICO": "rosario_atletico.png"
    }
    return mapping.get(nombre_equipo.upper(), "default.png")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logueado"):
            flash("Por favor inicie sesión para acceder a esta página.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def cargar_datos():
    try:
        if os.path.exists(Config.DATA_FILE):
            with open(Config.DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Opcional: Validar estructura básica de los datos cargados aquí
                if not isinstance(data, dict) or "partidos_jugados" not in data:
                    raise ValueError("Estructura de datos inválida")
                return data
        return inicializar_campeonato()
    except FileNotFoundError:
        logging.warning(f"Archivo de datos no encontrado: {Config.DATA_FILE}. Inicializando campeonato.")
        return inicializar_campeonato()
    except json.JSONDecodeError:
        logging.error(f"Error decodificando JSON de {Config.DATA_FILE}. El archivo puede estar corrupto.")
        flash("Error al leer el archivo de datos. El formato es incorrecto.", "error")
        return inicializar_campeonato() # Considerar si inicializar o fallar completamente
    except ValueError as e:
        logging.error(f"Error en la estructura de los datos cargados: {e}")
        flash("Error en la estructura de los datos. Se ha inicializado un nuevo campeonato.", "error")
        return inicializar_campeonato()
    except Exception as e:
        logging.error(f"Error desconocido al cargar datos: {str(e)}")
        flash("Error desconocido al cargar los datos.", "error")
        return inicializar_campeonato()

def guardar_datos(data):
    try:
        # Crear backup antes de guardar
        backup_data()
        
        with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info("Datos guardados exitosamente")
    except (IOError, OSError) as e:
        logging.error(f"Error de E/S al guardar datos: {str(e)}")
        flash("Error al guardar los datos en el archivo.", "error")
        raise # Propagar la excepción ya que no se pudo guardar
    except TypeError as e:
        logging.error(f"Error de tipo al serializar datos JSON: {str(e)}")
        flash("Error interno: No se pudieron guardar los datos debido a un formato incorrecto.", "error")
        raise
    except Exception as e:
        logging.error(f"Error guardando datos: {str(e)}")
        flash("Error al guardar los datos.", "error")
        raise

def inicializar_campeonato():
    data = {
        "partidos_jugados": [],
        "semifinales": [],
        "final": [],
        "ultima_actualizacion": datetime.now().isoformat()
    }
    guardar_datos(data)
    return data

def calcular_tabla_posiciones(partidos):
    tabla = {eq: {"Equipo": eq, "PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "PTS": 0} for eq in Config.EQUIPOS}
    for p in partidos:
        local = p["local"]
        visitante = p["visitante"]
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        tabla[local]["PJ"] += 1
        tabla[local]["GF"] += gl
        tabla[local]["GC"] += gv
        tabla[visitante]["PJ"] += 1
        tabla[visitante]["GF"] += gv
        tabla[visitante]["GC"] += gl
        if gl > gv:
            tabla[local]["PG"] += 1
            tabla[local]["PTS"] += 3
            tabla[visitante]["PP"] += 1
        elif gl < gv:
            tabla[visitante]["PG"] += 1
            tabla[visitante]["PTS"] += 3
            tabla[local]["PP"] += 1
        else:
            tabla[local]["PE"] += 1
            tabla[visitante]["PE"] += 1
            tabla[local]["PTS"] += 1
            tabla[visitante]["PTS"] += 1
    for eq in tabla.values():
        eq["DG"] = eq["GF"] - eq["GC"]
    return sorted(tabla.values(), key=lambda e: (e["PTS"], e["DG"], e["GF"]), reverse=True)

def calcular_goleadores(partidos):
    goleadores = {}
    for p in partidos:
        for g in p.get("goleadores", []):
            key = (g["nombre"].strip().upper(), g["equipo"].upper())
            if key not in goleadores:
                goleadores[key] = {"nombre": g["nombre"].strip(), "equipo": g["equipo"], "goles": 0}
            goleadores[key]["goles"] += int(g["cantidad"])
    return sorted(goleadores.values(), key=lambda g: g["goles"], reverse=True)

def probable_semifinal(tabla):
    if len(tabla) < 4:
        return []
    return [
        {
            "local": tabla[0]["Equipo"],
            "visitante": tabla[3]["Equipo"]
        },
        {
            "local": tabla[1]["Equipo"],
            "visitante": tabla[2]["Equipo"]
        }
    ]

def generar_semifinales(tabla):
    if len(tabla) < 4:
        return []
    return [
        {
            "id": 1,
            "local": tabla[0]["Equipo"],
            "visitante": tabla[3]["Equipo"],
            "goles_local": None,
            "goles_visitante": None,
            "jugado": False
        },
        {
            "id": 2,
            "local": tabla[1]["Equipo"],
            "visitante": tabla[2]["Equipo"],
            "goles_local": None,
            "goles_visitante": None,
            "jugado": False
        }
    ]

def generate_final_from_semis(semifinales):
    ganadores = []
    for sf in semifinales:
        if sf["goles_local"] > sf["goles_visitante"]:
            ganadores.append(sf["local"])
        elif sf["goles_local"] < sf["goles_visitante"]:
            ganadores.append(sf["visitante"])
        else:
            ganadores.append("Empate (definir)")
    if len(ganadores) == 2:
        return [{
            "local": ganadores[0],
            "visitante": ganadores[1],
            "goles_local": None,
            "goles_visitante": None,
            "jugado": False
        }]
    return []

def partidos_fixture_cargados(data, fecha):
    """Devuelve un set de tuplas (local, visitante) de partidos ya cargados para esa fecha."""
    return set(
        (p["local"], p["visitante"])
        for p in data["partidos_jugados"]
        if p["fecha"] == fecha
    )

def calcular_estadisticas_detalladas(partidos):
    """Calcula estadísticas detalladas del torneo"""
    stats = {
        'total_goles': 0,
        'goles_por_fecha': defaultdict(int),
        'goleadores_equipo': defaultdict(list),
        'partidos_jugados': len(partidos),
        'vallas_invictas': defaultdict(int)
    }
    
    # Calcular goles por fecha y total
    for partido in partidos:
        fecha = partido['fecha']
        goles_local = partido['goles_local']
        goles_visitante = partido['goles_visitante']
        stats['total_goles'] += goles_local + goles_visitante
        stats['goles_por_fecha'][fecha] += goles_local + goles_visitante
        
        # Contar vallas invictas
        if goles_visitante == 0:
            stats['vallas_invictas'][partido['local']] += 1
        if goles_local == 0:
            stats['vallas_invictas'][partido['visitante']] += 1
        
        # Agregar goleadores por equipo
        for goleador in partido.get('goleadores', []):
            equipo = goleador['equipo']
            nombre = goleador['nombre']
            goles = int(goleador['cantidad'])
            
            # Buscar si el goleador ya existe
            encontrado = False
            for g in stats['goleadores_equipo'][equipo]:
                if g['nombre'] == nombre:
                    g['goles'] += goles
                    encontrado = True
                    break
            
            if not encontrado:
                stats['goleadores_equipo'][equipo].append({
                    'nombre': nombre,
                    'goles': goles
                })
    
    # Ordenar goleadores por equipo
    for equipo in stats['goleadores_equipo']:
        stats['goleadores_equipo'][equipo].sort(key=lambda x: x['goles'], reverse=True)
    
    return stats

def calcular_evolucion_posiciones(partidos, equipos, fixture):
    posiciones_por_fecha = {eq: [] for eq in equipos}
    fechas = [f"Fecha {i}" for i in range(1, len(fixture) + 1)]
    partidos_por_fecha = {i: [] for i in range(1, len(fixture) + 1)}
    for p in partidos:
        partidos_por_fecha[p['fecha']].append(p)
    acumulados = []
    for fecha in range(1, len(fixture) + 1):
        acumulados.extend(partidos_por_fecha[fecha])
        tabla = calcular_tabla_posiciones(acumulados)
        # Mapeo de equipo a posición (1 = primero)
        posiciones = {t['Equipo']: idx + 1 for idx, t in enumerate(tabla)}
        for eq in equipos:
            posiciones_por_fecha[eq].append(posiciones.get(eq, len(equipos)))
    return posiciones_por_fecha, fechas

def calcular_mejor_racha(partidos, equipos):
    rachas = {eq: 0 for eq in equipos}
    max_rachas = {eq: 0 for eq in equipos}
    partidos_ordenados = sorted(partidos, key=lambda p: (p['fecha'], p.get('orden', 0)))
    for p in partidos_ordenados:
        for eq in equipos:
            if p['local'] == eq:
                if p['goles_local'] > p['goles_visitante']:
                    rachas[eq] += 1
                else:
                    rachas[eq] = 0
            elif p['visitante'] == eq:
                if p['goles_visitante'] > p['goles_local']:
                    rachas[eq] += 1
                else:
                    rachas[eq] = 0
            max_rachas[eq] = max(max_rachas[eq], rachas[eq])
    mejor_eq = max(max_rachas, key=lambda k: max_rachas[k])
    return {'nombre': mejor_eq, 'valor': max_rachas[mejor_eq]}

def calcular_mejor_defensa(tabla):
    mejor = min(tabla, key=lambda t: t['GC'])
    return {'nombre': mejor['Equipo'], 'valor': mejor['GC']}

def calcular_mas_goleado(tabla):
    peor = max(tabla, key=lambda t: t['GC'])
    return {'nombre': peor['Equipo'], 'valor': peor['GC']}

def find_next_match_info(partidos_jugados, fixture):
    """Encuentra la próxima fecha con partidos sin jugar y devuelve su número y partidos."""
    partidos_jugados_set = {(p["local"], p["visitante"]) for p in partidos_jugados}
    
    for i, fecha_partidos in enumerate(fixture):
        fecha_numero = i + 1
        partidos_sin_jugar_en_fecha = [
            p for p in fecha_partidos
            if (p["local"], p["visitante"]) not in partidos_jugados_set
        ]
        
        if partidos_sin_jugar_en_fecha:
            return fecha_numero, partidos_sin_jugar_en_fecha
            
    return None, [] # No hay más fechas pendientes

@app.route("/")
def index():
    try:
        data = cargar_datos()
        # Obtener partidos jugados y ordenarlos para mostrar en 'Partidos Jugados'
        partidos_jugados_ordenados = sorted(data["partidos_jugados"], 
                                         key=lambda p: (p["fecha"], data["partidos_jugados"].index(p)), 
                                         reverse=True)
        
        tabla = calcular_tabla_posiciones(data["partidos_jugados"])
        goleadores = calcular_goleadores(data["partidos_jugados"])
        semifinales = data.get("semifinales", [])
        final = data.get("final", [])
        probable = []
        
        # Encontrar la próxima fecha
        proxima_fecha, partidos_proxima_fecha = find_next_match_info(data["partidos_jugados"], FIXTURE)
        
        # Determinar si mostrar la probable semifinal
        if not semifinales and len(data["partidos_jugados"]) < 15:
            probable = probable_semifinal(tabla)
        
        return render_template(
            "index.html",
            tabla=tabla,
            partidos_jugados=partidos_jugados_ordenados,
            goleadores=goleadores,
            semifinales=semifinales,
            final=final,
            probable_semifinal=probable,
            escudo_equipo=escudo_equipo,
            fixture=FIXTURE,
            session=session,
            proxima_fecha=proxima_fecha,
            partidos_proxima_fecha=partidos_proxima_fecha
        )
    except Exception as e:
        logging.error(f"Error en index: {str(e)}")
        flash("Error al cargar la página principal.", "error")
        return render_template("error.html", error=str(e))

@app.route("/ingresar-resultado", methods=["GET", "POST"])
@login_required
def ingresar_resultado():
    data = cargar_datos()
    message = None
    fecha = int(request.args.get("fecha", 1))
    partidos_cargados = partidos_fixture_cargados(data, fecha)
    partidos_disponibles = [
        p for p in FIXTURE[fecha-1]
        if (p["local"], p["visitante"]) not in partidos_cargados
    ]
    if request.method == "POST":
        fecha = int(request.form.get("fecha"))
        local = request.form.get("local")
        visitante = request.form.get("visitante")
        goles_local_str = request.form.get("goles_local")
        goles_visitante_str = request.form.get("goles_visitante")
        
        # Validar que los equipos seleccionados correspondan a un partido disponible en la fecha
        partido_valido = any(p["local"] == local and p["visitante"] == visitante for p in FIXTURE[fecha-1])
        if not partido_valido:
            flash("Error: Los equipos seleccionados no corresponden a un partido válido para esta fecha.", "danger")
            return redirect(url_for("ingresar_resultado", fecha=fecha))
        
        # Validar goles locales y visitantes
        try:
            goles_local = int(goles_local_str)
            goles_visitante = int(goles_visitante_str)
            if goles_local < 0 or goles_visitante < 0:
                raise ValueError("Goles negativos")
        except (ValueError, TypeError):
            flash("Error: Los goles deben ser números enteros no negativos.", "danger")
            return redirect(url_for("ingresar_resultado", fecha=fecha))
        
        autores_goles = []
        for i in range(1, 11):
            nombre = request.form.get(f"goleador_nombre_{i}")
            equipo = request.form.get(f"goleador_equipo_{i}")
            cantidad = request.form.get(f"goleador_cantidad_{i}")
            if nombre and equipo and cantidad:
                # Validar goleador
                try:
                    cantidad_int = int(cantidad)
                    if cantidad_int < 0:
                        raise ValueError("Cantidad negativa")
                    if equipo not in [local, visitante]:
                        flash(f"Advertencia: Goleador {nombre} ({equipo}) no pertenece a los equipos del partido. Ignorado.", "warning")
                        continue # Ignorar goleador con equipo incorrecto
                    autores_goles.append({
                        "nombre": nombre.strip(),
                        "equipo": equipo,
                        "cantidad": cantidad_int
                    })
                except (ValueError, TypeError):
                    flash(f"Advertencia: La cantidad de goles para {nombre} debe ser un número entero no negativo. Entrada ignorada.", "warning")
                    continue # Ignorar entrada de goleador inválida
        
        for p in data["partidos_jugados"]:
            if (p["local"] == local and p["visitante"] == visitante) or (p["local"] == visitante and p["visitante"] == local):
                message = "Ese partido ya fue cargado."
                flash(message, "warning")
                return render_template("ingresar_resultado.html", 
                                    equipos=Config.EQUIPOS, 
                                    message=message, 
                                    session=session,
                                    escudo_equipo=escudo_equipo,
                                    partidos_disponibles=partidos_disponibles,
                                    fecha=fecha,
                                    fixture=FIXTURE)
        data["partidos_jugados"].append({
            "fecha": fecha,
            "local": local,
            "visitante": visitante,
            "goles_local": goles_local,
            "goles_visitante": goles_visitante,
            "goleadores": autores_goles
        })
        guardar_datos(data)
        return redirect(url_for("index"))
    return render_template("ingresar_resultado.html", 
                         equipos=Config.EQUIPOS, 
                         message=message, 
                         session=session,
                         escudo_equipo=escudo_equipo,
                         partidos_disponibles=partidos_disponibles,
                         fecha=fecha,
                         fixture=FIXTURE)

@app.route("/ingresar-semifinal", methods=["GET", "POST"])
@login_required
def ingresar_semifinal():
    data = cargar_datos()
    semifinales = data.get("semifinales", [])
    if not semifinales:
        return redirect(url_for("index"))
    if request.method == "POST":
        for sf in semifinales:
            goles_local = request.form.get(f"goles_local_{sf['id']}")
            goles_visitante = request.form.get(f"goles_visitante_{sf['id']}")
            if goles_local is not None and goles_visitante is not None:
                sf["goles_local"] = int(goles_local)
                sf["goles_visitante"] = int(goles_visitante)
                sf["jugado"] = True
        if all(sf.get("jugado") for sf in semifinales) and not data.get("final"):
            data["final"] = generate_final_from_semis(semifinales)
        data["semifinales"] = semifinales
        guardar_datos(data)
        return redirect(url_for("index"))
    return render_template("ingresar_semifinal.html", semifinales=semifinales, session=session)

@app.route("/ingresar-final", methods=["GET", "POST"])
@login_required
def ingresar_final():
    data = cargar_datos()
    final = data.get("final", [])
    if not final:
        return redirect(url_for("index"))
    if request.method == "POST":
        goles_local = request.form.get("goles_local")
        goles_visitante = request.form.get("goles_visitante")
        if goles_local is not None and goles_visitante is not None:
            final[0]["goles_local"] = int(goles_local)
            final[0]["goles_visitante"] = int(goles_visitante)
            final[0]["jugado"] = True
            data["final"] = final
            guardar_datos(data)
            return redirect(url_for("index"))
    return render_template("ingresar_final.html", final=final[0], session=session)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        if usuario == Config.USUARIO_ADMIN and contrasena == Config.CONTRASENA_ADMIN:
            session["logueado"] = True
            return redirect(url_for("index"))
        else:
            error = "Credenciales incorrectas."
    return render_template("login.html", error=error, session=session)

@app.route("/logout")
def logout():
    session.pop("logueado", None)
    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
@login_required
def reset():
    os.remove(Config.DATA_FILE)
    inicializar_campeonato()
    return redirect(url_for("index"))

@app.route("/estadisticas")
def estadisticas():
    try:
        data = cargar_datos()
        tabla = calcular_tabla_posiciones(data["partidos_jugados"])
        goleadores = calcular_goleadores(data["partidos_jugados"])
        # Calcular estadísticas detalladas
        stats = calcular_estadisticas_detalladas(data["partidos_jugados"])
        # Preparar datos para el gráfico
        fechas = [f"Fecha {i}" for i in range(1, len(FIXTURE) + 1)]
        goles_por_fecha = [stats['goles_por_fecha'].get(i, 0) for i in range(1, len(FIXTURE) + 1)]
        # Evolución de posiciones
        equipos = Config.EQUIPOS
        posiciones_por_fecha, fechas_evol = calcular_evolucion_posiciones(data["partidos_jugados"], equipos, FIXTURE)
        # Estadísticas de rachas y defensas
        mejor_racha = calcular_mejor_racha(data["partidos_jugados"], equipos)
        mejor_defensa = calcular_mejor_defensa(tabla)
        mas_goleado = calcular_mas_goleado(tabla)
        return render_template(
            "estadisticas.html",
            tabla=tabla,
            goleadores=goleadores,
            total_goles=stats['total_goles'],
            partidos_jugados=stats['partidos_jugados'],
            goleadores_equipo=stats['goleadores_equipo'],
            fechas=fechas,
            goles_por_fecha=goles_por_fecha,
            escudo_equipo=escudo_equipo,
            partidos=data["partidos_jugados"],
            equipos=equipos,
            posiciones_por_fecha=posiciones_por_fecha,
            mejor_racha=mejor_racha,
            mejor_defensa=mejor_defensa,
            mas_goleado=mas_goleado,
            vallas_invictas=stats['vallas_invictas']
        )
    except Exception as e:
        logging.error(f"Error en estadísticas: {str(e)}")
        flash("Error al cargar las estadísticas.", "error")
        return render_template("error.html", error=str(e))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')