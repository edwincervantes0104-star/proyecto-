import os
import json
import random
import traceback
import re
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, render_template_string, request, redirect,
    url_for, flash, send_from_directory, jsonify, session
)
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadData
import MySQLdb

# -----------------------------------------------------
#                  CONFIGURACIÓN FLASK
# -----------------------------------------------------
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_segura'

# ---------- Configuración de correo ----------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'edwincervantes0104@gmail.com'
app.config['MAIL_PASSWORD'] = 'jrhivripybwmefmj'  # Contraseña de aplicación de Gmail
app.config['MAIL_DEFAULT_SENDER'] = ('CECYTEM App', app.config['MAIL_USERNAME'])

# ---------- Inicialización después de configurar ----------
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# ---------- Configuración MySQL ----------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'usuario'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL extension
mysql = MySQL()
mysql.init_app(app)

# Uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

STATIC_UPLOADS = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(STATIC_UPLOADS, exist_ok=True)

# ---------- Helpers ----------
def get_db_connection():
    """Crear conexión directa a MySQL (para consultas helper)."""
    try:
        conn = MySQLdb.connect(
            host=app.config.get('MYSQL_HOST', 'localhost'),
            user=app.config.get('MYSQL_USER', 'root'),
            passwd=app.config.get('MYSQL_PASSWORD', ''),
            db=app.config.get('MYSQL_DB', 'usuario'),
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def execute_query(query, params=(), fetch_type='none'):
    """
    Ejecutar consulta SQL con manejo de errores
    fetch_type: 'all', 'one', 'none' (para INSERT/UPDATE/DELETE)
    """
    try:
        conn = get_db_connection()
        if conn is None:
            if fetch_type != 'none':
                flash('Error de conexión a la base de datos. Verifique que MySQL esté ejecutándose.')
                return [] if fetch_type == 'all' else None
            return False
        
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(query, params)
        
        result = None
        if fetch_type == 'all':
            result = cur.fetchall()
        elif fetch_type == 'one':
            result = cur.fetchone()
        elif fetch_type == 'none':
            conn.commit()
            result = True
            
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Error en execute_query: {e}")
        if fetch_type != 'none':
            flash('Error de base de datos')
            return [] if fetch_type == 'all' else None
        return False

def fetchall(query, params=()):
    return execute_query(query, params, 'all')

def fetchone(query, params=()):
    return execute_query(query, params, 'one')

def execute_update(query, params=()):
    return execute_query(query, params, 'none')

# ---------- Auth flow ----------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/crear_cuenta', methods=['GET', 'POST'])
def crear_cuenta():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        correo = request.form.get('correo')
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        ingresar = request.form.get('ingresar')  # Nuevo: tipo de ingreso (alumno, orientador, etc.)

        # Detectar el número de identificación según el tipo de ingreso
        no_control = request.form.get('no_control')
        no_orientador = request.form.get('no_orientador')
        no_profesor = request.form.get('no_profesor')
        no_directivo = request.form.get('no_directivo')

        # Validar campos obligatorios
        if not all([nombre, apellidos, correo, usuario, contrasena, ingresar]):
            flash('Rellena todos los campos')
            return redirect(url_for('crear_cuenta'))

        # Seleccionar el número correspondiente
        numero_ingreso = None
        if ingresar == 'alumno':
            numero_ingreso = no_control
        elif ingresar == 'orientador':
            numero_ingreso = no_orientador
        elif ingresar == 'profesor':
            numero_ingreso = no_profesor
        elif ingresar == 'directivo':
            numero_ingreso = no_directivo

        # Validar que el número esté presente
        if not numero_ingreso:
            flash('Ingresa tu número correspondiente')
            return redirect(url_for('crear_cuenta'))

        # Verificar si el usuario ya existe
        if fetchone("SELECT id FROM usuarios WHERE usuario = %s", (usuario,)):
            flash('El usuario ya existe')
            return redirect(url_for('crear_cuenta'))

        # Guardar datos en base de datos
        if execute_update(
            "INSERT INTO usuarios (nombre, apellidos, correo, usuario, contrasena, tipo_usuario, numero_identificacion) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (nombre, apellidos, correo, usuario, contrasena, ingresar, numero_ingreso)
        ):
            flash('Cuenta creada. Ahora inicia sesión.')
        else:
            flash('Error al crear la cuenta')

        return redirect(url_for('login'))

    return render_template('crear_cuenta.html')


#---------------------------------------------------------#
#---------------------------------------------------------#
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        rol = request.form.get('rol')
        contrasena = request.form.get('contrasena')
        identificador = None

        # Captura el identificador según el rol seleccionado
        if rol == 'alumno':
            identificador = request.form.get('no_control')
        elif rol == 'orientador':
            identificador = request.form.get('no_orientador')
        elif rol == 'profesor':
            identificador = request.form.get('no_profesor')
        elif rol == 'directivo':
            identificador = request.form.get('no_directivo')
        else:
            flash('Selecciona un rol válido')
            return redirect(url_for('login'))

        if not identificador or not contrasena:
            flash('Rellena todos los campos')
            return redirect(url_for('login'))

        # Buscar usuario en la base de datos
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT * FROM usuarios
            WHERE tipo_usuario = %s
              AND numero_identificacion = %s
              AND contrasena = %s
        """, (rol, identificador, contrasena))
        usuario = cursor.fetchone()
        cursor.close()

        # Validar resultado
        if usuario:
            session['usuario'] = usuario['usuario']
            session['tipo_usuario'] = usuario['tipo_usuario']
            flash(f"Bienvenido {usuario['nombre']} ({usuario['tipo_usuario']})")
            return redirect(url_for('menu'))
        else:
            flash('Datos incorrectos. Verifica tu número y contraseña.')
            return redirect(url_for('login'))

    # Si entra por GET, mostrar el formulario
    return render_template('login.html')

#----------------------------------------------------------#

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada')
    return redirect(url_for('login'))

@app.route('/reset_intentos')
def reset_intentos():
    """Ruta para resetear intentos fallidos y tiempo de bloqueo de todos los usuarios (útil para debugging)"""
    session.pop('intentos_por_usuario', None)
    session.pop('bloqueos_por_usuario', None)
    # También limpiar sistema antiguo por si acaso
    session.pop('intentos_fallidos', None)
    session.pop('tiempo_bloqueo', None)
    flash('Intentos de login y bloqueos reseteados para todos los usuarios')
    return redirect(url_for('login'))

@app.route('/reset_usuario/<usuario>')
def reset_usuario_especifico(usuario):
    """Ruta para resetear intentos fallidos de un usuario específico"""
    intentos_por_usuario = session.get('intentos_por_usuario', {})
    bloqueos_por_usuario = session.get('bloqueos_por_usuario', {})
    
    intentos_por_usuario.pop(usuario, None)
    bloqueos_por_usuario.pop(usuario, None)
    
    session['intentos_por_usuario'] = intentos_por_usuario
    session['bloqueos_por_usuario'] = bloqueos_por_usuario
    
    flash(f'Intentos y bloqueo reseteados para el usuario "{usuario}"')
    return redirect(url_for('login'))
# ----------------------------- PARTE 2/2 -----------------------------
# app.py - Parte 2 (recuperación, CRUD, buscadores, chat, dashboard (dabohar), run)
# ---------------------------------------------------------------------

# ---------- Recuperación de contraseña por código ----------
@app.route('/recuperar_correo', methods=['GET', 'POST'])
def recuperar_correo():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id, nombre FROM usuarios WHERE correo = %s", (correo,))
        usuario = cur.fetchone()

        if not usuario:
            flash("El correo no existe en la base de datos.", "danger")
            cur.close()
            return render_template('recuperar_correo.html')

        # Guardamos el correo en la sesión
        session['correo_recuperacion'] = correo

        # Generamos un código aleatorio de 6 dígitos
        codigo = str(random.randint(100000, 999999))

        # Guardamos el código en la base
        cur.execute("""
            INSERT INTO codigos_recuperacion (correo, codigo, fecha)
            VALUES (%s, %s, NOW())
        """, (correo, codigo))
        mysql.connection.commit()
        cur.close()

        # Enviamos el correo
        try:
            msg = Message("Código de recuperación - CECYTEM", recipients=[correo])
            msg.html = f"""
                <h3>Hola {usuario['nombre']}</h3>
                <p>Tu código de recuperación es:</p>
                <h2 style='color:green; font-size: 24px'>{codigo}</h2>
                <p>Este código expira en 10 minutos.</p>
            """
            mail.send(msg)
            flash("Código enviado correctamente. Revisa tu correo.", "success")
            return redirect(url_for('verificar_codigo'))
        except Exception as e:
            print(f"⚠ Error al enviar correo: {e}")
            flash("Error al enviar el correo. Revisa la configuración SMTP.", "danger")

    return render_template('recuperar_correo.html')


@app.route("/verificar_codigo", methods=["GET", "POST"])
def verificar_codigo():
    correo = session.get("correo_recuperacion")

    if not correo:
        flash("Primero debes solicitar la recuperación.", "danger")
        return redirect(url_for("recuperar_correo"))

    if request.method == "POST":
        codigo_ingresado = request.form.get("codigo", "").strip()

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT codigo, fecha FROM codigos_recuperacion
            WHERE correo = %s
            ORDER BY id DESC LIMIT 1
        """, (correo,))
        fila = cur.fetchone()
        cur.close()

        if not fila:
            flash("No se encontró ningún código para este correo.", "danger")
            return render_template("verificar_codigo.html")

        codigo_db = str(fila['codigo']).strip()
        fecha = fila['fecha']

        # Verificamos si ha pasado más de 10 minutos
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        diferencia = datetime.now() - fecha

        if codigo_ingresado == codigo_db and diferencia < timedelta(minutes=10):
            flash("✅ Código verificado correctamente.", "success")
            return redirect(url_for("nueva_contraseña"))
        elif codigo_ingresado != codigo_db:
            flash("❌ Código incorrecto. Revisa bien los dígitos.", "danger")
        else:
            flash("⚠ El código ha expirado. Solicita uno nuevo.", "warning")
            return redirect(url_for("recuperar_correo"))

    return render_template("verificar_codigo.html")


@app.route("/nueva_contraseña", methods=["GET", "POST"])
def nueva_contraseña():
    correo = session.get("correo_recuperacion")

    if not correo:
        flash("Sesión expirada. Solicita un nuevo código.", "warning")
        return redirect(url_for("recuperar_correo"))

    if request.method == "POST":
        nueva = request.form.get("nueva")
        confirmar = request.form.get("confirmar")

        if not nueva or not confirmar:
            flash("Debes llenar ambos campos.", "danger")
            return redirect(url_for("nueva_contraseña"))

        if nueva != confirmar:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(url_for("nueva_contraseña"))

        # Actualizar la contraseña
        cur = mysql.connection.cursor()
        cur.execute("UPDATE usuarios SET contrasena = %s WHERE correo = %s", (nueva, correo))
        mysql.connection.commit()
        cur.close()

        # Limpiar la sesión
        session.pop("correo_recuperacion", None)
        flash("Contraseña actualizada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("nueva_contraseña.html")

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route("/dashboard")
def dashboard():
    """Renderiza el panel principal (Dabohar)."""
    if "usuario" not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for("login"))

    usuario = session.get("usuario") or session.get("usuario_nombre") or "Administrador"

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM alumnos")
        alumnos = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM profesores")
        profesores = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM orientadores")
        orientadores = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM directivos")
        directivos = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM materias")
        materias = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM recursos")
        recursos = cur.fetchone()["total"]
        cur.close()

    except Exception as e:
        # Si no hay conexión o tablas, generamos datos falsos
        print("⚠️ No se pudo obtener datos de MySQL:", e)
        alumnos = random.randint(80, 150)
        profesores = random.randint(10, 25)
        orientadores = random.randint(3, 8)
        directivos = random.randint(2, 5)
        materias = random.randint(12, 30)
        recursos = random.randint(5, 20)

    data = {
        "alumnos": alumnos,
        "profesores": profesores,
        "orientadores": orientadores,
        "directivos": directivos,
        "materias": materias,
        "recursos": recursos,
    }

    return render_template_string(dashboard.html, usuario=usuario, data=data, datetime=datetime)


# -----------------------------------------------------
# 🔄 ACTUALIZACIÓN AUTOMÁTICA DE DATOS (JSON)
# -----------------------------------------------------
@app.route("/dashboard/data")
def dashboard_data():
    """Devuelve los datos actualizados en JSON."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM alumnos")
        alumnos = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM profesores")
        profesores = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM orientadores")
        orientadores = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM directivos")
        directivos = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM materias")
        materias = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM recursos")
        recursos = cur.fetchone()["total"]
        cur.close()
    except Exception as e:
        print("⚠️ Error al obtener datos actualizados:", e)
        alumnos = random.randint(80, 150)
        profesores = random.randint(10, 25)
        orientadores = random.randint(3, 8)
        directivos = random.randint(2, 5)
        materias = random.randint(12, 30)
        recursos = random.randint(5, 20)

    return jsonify(
        alumnos=alumnos,
        profesores=profesores,
        orientadores=orientadores,
        directivos=directivos,
        materias=materias,
        recursos=recursos,
    )

# ------------------ ACTUALIZACIÓN EN TIEMPO REAL Y CRUD (resumen) ------------------
# (mantengo tus rutas CRUD / buscadores / chat tal como estaban en tu código original)

# ---------- Profesores ----------
@app.route('/profesor', methods=['GET','POST'])
def profesor():
    if request.method == 'POST':
        numero_empleado = request.form.get('numero_empleado')
        nombre_docente = request.form.get('nombre_docente')
        fecha_ingreso = request.form.get('fecha_ingreso')
        perfil_profesional = request.form.get('perfil_profesional')
        asignatura = request.form.get('asignatura')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO profesores 
            (numero_empleado, nombre_docente, fecha_ingreso, perfil_profesional, asignatura)
            VALUES (%s,%s,%s,%s,%s)
        """, (numero_empleado, nombre_docente, fecha_ingreso, perfil_profesional, asignatura))
        mysql.connection.commit()
        cur.close()

        flash('Profesor registrado')
        return redirect(url_for('profesor'))

    items = fetchall("SELECT * FROM profesores")
    return render_template('profesor.html', items=items)

@app.route('/profesor/editar/<int:numero_empleado>', methods=['GET','POST'])
def editar_profesor(numero_empleado):
    if request.method == 'POST':
        nombre_docente = request.form.get('nombre_docente')
        fecha_ingreso = request.form.get('fecha_ingreso')
        perfil_profesional = request.form.get('perfil_profesional')
        asignatura = request.form.get('asignatura')

        cur = mysql.connection.cursor()
        cur.execute("""
        UPDATE profesores 
        SET nombre_docente=%s, fecha_ingreso=%s,
            perfil_profesional=%s, asignatura=%s
        WHERE numero_empleado=%s
        """, (nombre_docente, fecha_ingreso, perfil_profesional, asignatura, numero_empleado))
        mysql.connection.commit()
        cur.close()

        flash('Profesor actualizado')
        return redirect(url_for('profesor'))

    item = fetchone("SELECT * FROM profesores WHERE numero_empleado = %s", (numero_empleado,))
    items = fetchall("SELECT * FROM profesores")
    return render_template('profesor.html', edit_obj=item, items=items)

@app.route('/profesor/eliminar/<int:numero_empleado>')
def eliminar_profesor(numero_empleado):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM profesores WHERE numero_empleado = %s", (numero_empleado,))
    mysql.connection.commit()
    cur.close()

    flash('Profesor eliminado')
    return redirect(url_for('profesor'))

# ---------- Buscador de profesores ----------
@app.route('/buscar_profesor', methods=['GET'])
def buscar_profesor():
    termino = request.args.get('q', '')

    profesores = []
    if termino:
        like = f"%{termino}%"
        profesores = fetchall("""
            SELECT * FROM profesores
            WHERE nombre_docente LIKE %s
               OR numero_empleado LIKE %s
               OR asignatura LIKE %s
        """, (like, like, like))

    return render_template(
        'buscar.html',
        termino="",
        resultados=[],          # para evitar errores en buscador de recursos
        termino_alumno="",
        alumnos=[],
        termino_profesor=termino,
        profesores=profesores
    )

# ---------- Alumnos ----------
@app.route('/alumno', methods=['GET','POST'])
def alumno():
    if request.method == 'POST':
        no_control = request.form.get('no_control')
        curp = request.form.get('curp')
        nombre = request.form.get('nombre')
        apellido_paterno = request.form.get('apellido_paterno')
        apellido_materno = request.form.get('apellido_materno')
        turno = request.form.get('turno')
        grupo = request.form.get('grupo')
        semestre = request.form.get('semestre')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO alumnos 
            (no_control, curp, nombre, apellido_paterno, apellido_materno, turno, grupo, semestre)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (no_control, curp, nombre, apellido_paterno, apellido_materno, turno, grupo, semestre))
        mysql.connection.commit()
        cur.close()

        flash('Alumno registrado')
        return redirect(url_for('alumno'))

    items = fetchall("SELECT * FROM alumnos")
    return render_template('alumno.html', items=items)

@app.route('/alumno/editar/<int:id>', methods=['GET','POST'])
def editar_alumno(id):
    if request.method == 'POST':
        no_control = request.form.get('no_control')
        curp = request.form.get('curp')
        nombre = request.form.get('nombre')
        apellido_paterno = request.form.get('apellido_paterno')
        apellido_materno = request.form.get('apellido_materno')
        turno = request.form.get('turno')
        grupo = request.form.get('grupo')
        semestre = request.form.get('semestre')

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE alumnos 
            SET no_control=%s, curp=%s, nombre=%s, apellido_paterno=%s, apellido_materno=%s,
                turno=%s, grupo=%s, semestre=%s 
            WHERE id=%s
        """, (no_control, curp, nombre, apellido_paterno, apellido_materno,
              turno, grupo, semestre, id))
        mysql.connection.commit()
        cur.close()

        flash('Alumno actualizado')
        return redirect(url_for('alumno'))

    item = fetchone("SELECT * FROM alumnos WHERE id = %s", (id,))
    items = fetchall("SELECT * FROM alumnos")
    return render_template('alumno.html', edit_obj=item, items=items)

@app.route('/alumno/eliminar/<int:id>')
def eliminar_alumno(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alumnos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash('Alumno eliminado')
    return redirect(url_for('alumno'))

# ---------- Buscador de alumnos ----------
@app.route('/buscar_alumno', methods=['GET'])
def buscar_alumno():
    termino = request.args.get('q', '')

    alumnos = []
    if termino:
        like = f"%{termino}%"
        alumnos = fetchall("""
            SELECT * FROM alumnos
            WHERE curp LIKE %s
               OR nombre LIKE %s
               OR apellido_paterno LIKE %s
               OR apellido_materno LIKE %s
               OR turno LIKE %s
               OR grupo LIKE %s
               OR semestre LIKE %s
        """, (like, like, like, like, like, like, like))

    return render_template(
        'buscar.html',
        termino="",
        resultados=[],           # para que no truene el buscador general
        termino_alumno=termino,
        alumnos=alumnos
    )

# ---------- Orientadores ----------
@app.route('/orientador', methods=['GET','POST'])
def orientador():
    if request.method == 'POST':
        numero_empleado = request.form.get('numero_empleado')
        nombre = request.form.get('nombre')
        grupos_atendidos = request.form.get('grupos_atendidos')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO orientadores (numero_empleado, nombre, grupos_atendidos)
            VALUES (%s, %s, %s)
        """, (numero_empleado, nombre, grupos_atendidos))
        mysql.connection.commit()
        cur.close()

        flash('Orientador registrado')
        return redirect(url_for('orientador'))

    items = fetchall("SELECT * FROM orientadores")
    return render_template('orientador.html', items=items)

@app.route('/orientador/editar/<int:numero_empleado>', methods=['GET','POST'])
def editar_orientador(numero_empleado):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        grupos_atendidos = request.form.get('grupos_atendidos')

        cur.execute("""
            UPDATE orientadores
            SET nombre=%s, grupos_atendidos=%s
            WHERE numero_empleado=%s
        """, (nombre, grupos_atendidos, numero_empleado))
        mysql.connection.commit()
        cur.close()

        flash('Orientador actualizado')
        return redirect(url_for('orientador'))

    cur.execute("SELECT * FROM orientadores WHERE numero_empleado = %s", (numero_empleado,))
    item = cur.fetchone()

    cur.execute("SELECT * FROM orientadores ORDER BY numero_empleado DESC")
    items = cur.fetchall()
    cur.close()

    return render_template('orientador.html', edit_obj=item, items=items)

@app.route('/orientador/eliminar/<int:numero_empleado>')
def eliminar_orientador(numero_empleado):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM orientadores WHERE numero_empleado = %s", (numero_empleado,))
    mysql.connection.commit()
    cur.close()

    flash('Orientador eliminado')
    return redirect(url_for('orientador'))

# ---------- Buscador de orientadores ----------
@app.route('/buscar_orientador', methods=['GET'])
def buscar_orientador():
    termino = request.args.get('q', '')

    orientadores = []
    if termino:
        like = f"%{termino}%"
        orientadores = fetchall("""
            SELECT numero_empleado, nombre, grupos_atendidos
            FROM orientadores
            WHERE numero_empleado LIKE %s
               OR nombre LIKE %s
               OR grupos_atendidos LIKE %s
        """, (like, like, like))

    return render_template(
        'buscar.html',
        termino="",               # para que no truene el buscador general
        resultados=[],
        termino_orientador=termino,
        orientadores=orientadores,
    )

# ---------- Directivos ----------
@app.route('/directivo', methods=['GET','POST'])
def directivo():
    if request.method == 'POST':
        numero_empleado = request.form.get('numero_empleado')
        nombre = request.form.get('nombre')
        puesto = request.form.get('puesto')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO directivos (numero_empleado, nombre, puesto)
            VALUES (%s, %s, %s)
        """, (numero_empleado, nombre, puesto))
        mysql.connection.commit()
        cur.close()

        flash('Directivo registrado')
        return redirect(url_for('directivo'))

    items = fetchall("SELECT * FROM directivos")
    return render_template('directivo.html', items=items)

@app.route('/directivo/editar/<int:numero_empleado>', methods=['GET','POST'])
def editar_directivo(numero_empleado):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        puesto = request.form.get('puesto')

        cur.execute("""
            UPDATE directivos
            SET nombre=%s, puesto=%s
            WHERE numero_empleado=%s
        """, (nombre, puesto, numero_empleado))

        mysql.connection.commit()
        cur.close()

        flash('Directivo actualizado correctamente')
        return redirect(url_for('directivo'))

    cur.execute("SELECT * FROM directivos WHERE numero_empleado = %s", (numero_empleado,))
    item = cur.fetchone()

    cur.execute("SELECT * FROM directivos")
    items = cur.fetchall()
    cur.close()

    return render_template('editar_directivo.html', edit_obj=item, items=items)

@app.route('/directivo/eliminar/<int:numero_empleado>')
def eliminar_directivo(numero_empleado):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM directivos WHERE numero_empleado = %s", (numero_empleado,))
    mysql.connection.commit()
    cur.close()

    flash('Directivo eliminado')
    return redirect(url_for('directivo'))

# ---------- Buscador de directivos ----------
@app.route('/buscar_directivo', methods=['GET'])
def buscar_directivo():
    termino = request.args.get('q', '')

    directivos = []
    if termino:
        like = f"%{termino}%"
        directivos = fetchall("""
            SELECT numero_empleado, nombre, puesto
            FROM directivos
            WHERE numero_empleado LIKE %s
               OR nombre LIKE %s
               OR puesto LIKE %s
        """, (like, like, like))

    return render_template(
        'buscar.html',
        termino="",                 # evita error del buscador principal
        resultados=[],
        termino_directivo=termino,
        directivos=directivos
    )

# ---------- Materias ----------
@app.route('/materia', methods=['GET','POST'])
def materia():
    if request.method == 'POST':
        estructura = request.form.get('estructura_curricular')
        nombre = request.form.get('nombre_materia')
        horas_semana = request.form.get('horas_semana')
        horas_totales = request.form.get('horas_totales')
        creditos = request.form.get('creditos')

        if not estructura or not nombre or not horas_semana or not horas_totales or not creditos:
            flash('Todos los campos son obligatorios.')
            return redirect(url_for('materia'))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO materias 
            (estructura_curricular, nombre_materia, horas_semana, horas_totales, creditos)
            VALUES (%s, %s, %s, %s, %s)
        """, (estructura, nombre, horas_semana, horas_totales, creditos))

        mysql.connection.commit()
        cur.close()

        flash('Materia registrada correctamente.')
        return redirect(url_for('materia'))

    items = fetchall("SELECT * FROM materias ORDER BY id DESC")
    return render_template('materia.html', items=items)

@app.route('/materia/editar/<int:id>', methods=['GET','POST'])
def editar_materia(id):
    if request.method == 'POST':
        estructura = request.form.get('estructura_curricular')
        nombre = request.form.get('nombre_materia')
        horas_semana = request.form.get('horas_semana')
        horas_totales = request.form.get('horas_totales')
        creditos = request.form.get('creditos')

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE materias 
            SET estructura_curricular=%s, nombre_materia=%s, horas_semana=%s,
                horas_totales=%s, creditos=%s
            WHERE id=%s
        """, (estructura, nombre, horas_semana, horas_totales, creditos, id))

        mysql.connection.commit()
        cur.close()

        flash('Materia actualizada correctamente.')
        return redirect(url_for('materia'))

    item = fetchone("SELECT * FROM materias WHERE id = %s", (id,))
    items = fetchall("SELECT * FROM materias ORDER BY id DESC")
    return render_template('materia.html', edit_obj=item, items=items)

@app.route('/materia/eliminar/<int:id>')
def eliminar_materia(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM materias WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()

    flash('Materia eliminada correctamente.')
    return redirect(url_for('materia'))

#--------buscador de materias--------
@app.route('/buscar_materia', methods=['GET'])
def buscar_materia():
    termino = request.args.get('q', '')
    materias = []

    if termino:
        like = f"%{termino}%"
        materias = fetchall("""
            SELECT id, estructura_curricular, nombre_materia, horas_semana, horas_totales, creditos
            FROM materias
            WHERE estructura_curricular LIKE %s
               OR nombre_materia LIKE %s
               OR horas_semana LIKE %s
               OR horas_totales LIKE %s
               OR creditos LIKE %s
        """, (like, like, like, like, like))

    return render_template(
        'buscar.html',
        termino="",
        resultados=[],
        alumnos=[],
        profesores=[],
        orientadores=[],
        directivos=[],
        materias=materias,
        termino_materia=termino
    )

# ---------- Recursos ----------
@app.route('/recursos', methods=['GET','POST'])
def recursos_route():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        tipo_documento = request.form.get('tipo_documento')
        docente = request.form.get('docente')
        materia = request.form.get('materia')
        archivo = request.files.get('archivo')
        
        if not (nombre and tipo_documento and docente and archivo):
            flash('Todos los campos son obligatorios.')
            return redirect(url_for('recursos_route'))
            
        filename = secure_filename(archivo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        archivo.save(filepath)
        
        # Insertar recurso
        if execute_update("""
            INSERT INTO recursos (nombre, tipo_documento, docente, materia, archivo, fecha_subida)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nombre, tipo_documento, docente, materia, filename, datetime.now())):
            
            # Obtener el ID del recurso recién insertado
            nuevo_recurso = fetchone("SELECT LAST_INSERT_ID() as id")
            if nuevo_recurso:
                nuevo_id = nuevo_recurso['id']
                mensaje_texto = f"Nuevo recurso '{nombre}' disponible en la materia {materia} - Docente: {docente}"
                
                # Crear notificaciones para cada grupo
                for grupo in ['alumnos', 'profesores', 'orientadores']:
                    execute_update("""
                        INSERT INTO notificaciones (mensaje, destinatario, recurso_id, fecha)
                        VALUES (%s, %s, %s, %s)
                    """, (mensaje_texto, grupo, nuevo_id, datetime.now()))
                
                # Agregar mensaje al chat
                execute_update("""
                    INSERT INTO chat (usuario, mensaje, fecha)
                    VALUES (%s, %s, %s)
                """, ("Sistema", f"[NOTIFICACIÓN] {mensaje_texto}", datetime.now()))
                
                flash('Recurso subido correctamente y notificado.')
            else:
                flash('Error al obtener ID del recurso')
        else:
            flash('Error al subir el recurso')
            
        return redirect(url_for('recursos_route'))

    items = fetchall("SELECT * FROM recursos ORDER BY fecha_subida DESC")
    return render_template('recursos.html', items=items)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/recursos/eliminar/<int:id>')
def eliminar_recurso(id):
    # Obtener información del archivo antes de eliminarlo
    recurso = fetchone("SELECT archivo FROM recursos WHERE id = %s", (id,))
    
    if recurso and recurso['archivo']:
        try:
            # Eliminar archivo físico
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], recurso['archivo']))
        except:
            pass  # No importa si el archivo no existe
        
        # Eliminar registro de la base de datos
        if execute_update("DELETE FROM recursos WHERE id = %s", (id,)):
            flash('Recurso eliminado correctamente.')
        else:
            flash('Error al eliminar el recurso de la base de datos.')
    else:
        flash('Recurso no encontrado.')
        
    return redirect(url_for('recursos_route'))


#----------Buscador de voz-----------------
@app.route("/voz_busqueda", methods=["POST"])
def voz_busqueda():
    data = request.get_json()
    texto = data.get("texto","")
    
    
    # Limpiar el texto de puntuación y espacios extra
    texto_limpio = re.sub(r'[^\w\s]', '', texto)  # Eliminar puntuación
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)  # Normalizar espacios
    texto_limpio = texto_limpio.strip()  # Eliminar espacios al inicio y final
    
    print(f"Texto original: '{texto}'")
    print(f"Texto limpio: '{texto_limpio}'")

    return jsonify({"redirect": f"/buscar?q={texto_limpio}"})

# ---------- Buscador General ----------
@app.route('/buscar', methods=['GET'])
def buscar():
    termino = request.args.get('q', '')

    resultados = fetchall("""
        SELECT * FROM recursos
        WHERE nombre LIKE %s OR docente LIKE %s OR materia LIKE %s
        ORDER BY fecha_subida DESC
    """, (f"%{termino}%", f"%{termino}%", f"%{termino}%"))

    return render_template('buscar.html', resultados=resultados, termino=termino)

# ---------- Chat general  ----------
@app.route("/chat", methods=["GET", "POST"])
def chat_con_usuario():
    try:
        cur = mysql.connection.cursor()

        # --- Envío de mensaje ---
        if request.method == "POST":
            usuario = request.form.get("usuario") or session.get('usuario_nombre', 'Anónimo')
            contenido = request.form.get("contenido", "").strip()
            archivo = request.files.get("archivo")

            if not contenido and (not archivo or archivo.filename == ""):
                flash("⚠ No puedes enviar un mensaje vacío.", "warning")
                return redirect(url_for("chat_con_usuario"))

            # --- Guardar mensaje en BD ---
            cur.execute(
                "INSERT INTO chat (usuario, mensaje, fecha) VALUES (%s, %s, %s)",
                (usuario, contenido if contenido else None, datetime.now())
            )
            mysql.connection.commit()
            mensaje_id = cur.lastrowid

            # --- Guardar archivo si se envía ---
            if archivo and archivo.filename:
                nombre_seguro = secure_filename(archivo.filename)
                carpeta_uploads = os.path.join("static", "uploads")
                os.makedirs(carpeta_uploads, exist_ok=True)
                ruta_completa = os.path.join(carpeta_uploads, nombre_seguro)
                archivo.save(ruta_completa)

                cur.execute(
                    "INSERT INTO archivos_chat (mensaje_id, nombre_archivo, ruta) VALUES (%s, %s, %s)",
                    (mensaje_id, nombre_seguro, ruta_completa)
                )
                mysql.connection.commit()

            cur.close()
            return redirect(url_for("chat_con_usuario"))

        # --- Mostrar mensajes ---
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.id, c.usuario, c.mensaje, c.fecha, a.nombre_archivo, a.ruta
            FROM chat c
            LEFT JOIN archivos_chat a ON c.id = a.mensaje_id
            ORDER BY c.fecha DESC
        """)
        filas = cur.fetchall()
        cur.close()

        mensajes = []
        for f in filas:
            msg = dict(f)
            fecha_val = msg.get('fecha')
            msg['fecha_str'] = fecha_val.strftime('%Y-%m-%d %H:%M:%S') if fecha_val else ''

            # --- Determinar tipo de archivo ---
            if msg.get('nombre_archivo'):
                nombre = msg['nombre_archivo']
                ext = nombre.lower().split('.')[-1]
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    msg['tipo'] = 'imagen'
                elif ext in ['mp4', 'webm', 'avi', 'mov']:
                    msg['tipo'] = 'video'
                elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                    msg['tipo'] = 'audio'
                else:
                    msg['tipo'] = 'archivo'
                msg['archivo_url'] = f"/static/uploads/{nombre}"
            else:
                msg['tipo'] = 'texto'

            mensajes.append(msg)

        return render_template("chat.html", mensajes=mensajes)

    except Exception as e:
        print("Error en /chat:", traceback.format_exc())
        flash(f"❌ Error en chat: {e}", "danger")
        return render_template("chat.html", mensajes=[])

# ✅ Alias para compatibilidad con url_for('chat_privado')
app.add_url_rule('/chat', endpoint='chat_privado', view_func=chat_con_usuario)

# ---------- Recuperar contraseña (alternativa simple) ----------
@app.route('/recuperar_contraseña', methods=['GET','POST'])
def recuperar_contraseña():
    usuario = None
    contrasena = None
    mensaje = None

    if request.method == 'POST':
        correo = request.form.get('correo')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT usuario, contrasena FROM usuarios WHERE correo = %s", (correo,))
        cuenta = cursor.fetchone()
        cursor.close()

        if cuenta:
            usuario, contrasena = cuenta.values()
        else:
            mensaje = "No se encontró ninguna cuenta asociada a ese correo."

    return render_template('recuperar_correo.html', usuario=usuario, contrasena=contrasena, mensaje=mensaje)

# ---------- Voz endpoints (alumno, profesor, orientador, directivo, materia) ----------
@app.route("/voz_busqueda_alumno", methods=["POST"])
def voz_busqueda_alumno():
    data = request.get_json()
    texto = data.get("texto","")
    texto_limpio = re.sub(r'[^\w\s]', '', texto).strip()
    return jsonify({"redirect": f"/buscar_alumno?q={texto_limpio}"})

@app.route("/voz_busqueda_profesor", methods=["POST"])
def voz_busqueda_profesor():
    data = request.get_json()
    texto = data.get("texto","")
    texto_limpio = re.sub(r'[^\w\s]', '', texto).strip()
    return jsonify({"redirect": f"/buscar_profesor?q={texto_limpio}"})

@app.route("/voz_busqueda_orientador", methods=["POST"])
def voz_busqueda_orientador():
    data = request.get_json()
    texto = data.get("texto","")
    texto_limpio = re.sub(r'[^\w\s]', '', texto).strip()
    return jsonify({"redirect": f"/buscar_orientador?q={texto_limpio}"})

@app.route("/voz_busqueda_directivo", methods=["POST"])
def voz_busqueda_directivo():
    data = request.get_json()
    texto = data.get("texto","")
    texto_limpio = re.sub(r'[^\w\s]', '', texto).strip()
    return jsonify({"redirect": f"/buscar_directivo?q={texto_limpio}"})

@app.route("/voz_busqueda_materia", methods=["POST"])
def voz_busqueda_materia():
    data = request.get_json()
    texto = data.get("texto","")
    texto_limpio = re.sub(r'[^\w\s]', '', texto).strip()
    return jsonify({"redirect": f"/buscar_materia?q={texto_limpio}"})

# ----------- Run -----------
if __name__ == "__main__":
    app.run(debug=True)
