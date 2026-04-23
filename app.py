import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")


# ── helpers ──────────────────────────────────────────────────────────────────

def get_conexao():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "saude_mental"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def calcular_nivel(media):
    if media <= 3:
        return "leve"
    elif media <= 6:
        return "moderado"
    else:
        return "intenso"

@app.route("/", methods=["GET", "POST"])
def home():
    resultado = ""
    nivel = ""
    erro = ""

    if request.method == "POST":
        nome      = request.form.get("nome", "").strip()
        idade     = request.form.get("idade", "").strip()
        sexo      = request.form.get("sexo", "").strip()
        ansiedade = request.form.get("ansiedade", "").strip()
        estresse  = request.form.get("estresse", "").strip()
        depressao = request.form.get("depressao", "").strip()

        if not all([nome, idade, sexo, ansiedade, estresse, depressao]):
            erro = "Preencha todos os campos antes de enviar!"
        else:
            try:
                idade     = int(idade)
                ansiedade = int(ansiedade)
                estresse  = int(estresse)
                depressao = int(depressao)

                if not (0 < idade < 120):
                    erro = "Idade inválida!"
                elif not (0 <= ansiedade <= 10 and 0 <= estresse <= 10 and 0 <= depressao <= 10):
                    erro = "Os valores devem estar entre 0 e 10!"
                else:
                    media = (ansiedade + estresse + depressao) / 3
                    nivel = calcular_nivel(media)

                    conexao = get_conexao()
                    cursor  = conexao.cursor()
                    try:
                        sql = "INSERT INTO usuarios (nome, idade, sexo, ansiedade, estresse, depressao, nivel) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                        cursor.execute(sql, (nome, idade, sexo, ansiedade, estresse, depressao, nivel))
                        conexao.commit()
                    finally:
                        cursor.close()
                        conexao.close()

                    resultado = f"Nível: {nivel} (média {media:.1f})"

            except ValueError:
                erro = "Idade e notas precisam ser números válidos!"

    return render_template("index.html", resultado=resultado, nivel=nivel, erro=erro)


# ── painel admin ──────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    conexao = get_conexao()
    cursor  = conexao.cursor()
    try:
        cursor.execute("SELECT id, nome, idade, sexo, ansiedade, estresse, depressao, nivel FROM usuarios ORDER BY id")
        registros = cursor.fetchall()
    finally:
        cursor.close()
        conexao.close()

    return render_template("admin.html", registros=registros)


@app.route("/admin/editar", methods=["POST"])
def admin_editar():
    try:
        id_usuario = int(request.form["id"])
        nome       = request.form["nome"].strip()
        idade      = int(request.form["idade"])
        sexo       = request.form["sexo"].strip()
        ansiedade  = int(request.form["ansiedade"])
        estresse   = int(request.form["estresse"])
        depressao  = int(request.form["depressao"])

        if not (0 < idade < 120):
            flash("Idade inválida.", "error")
            return redirect(url_for("admin"))

        if not (0 <= ansiedade <= 10 and 0 <= estresse <= 10 and 0 <= depressao <= 10):
            flash("Valores de ansiedade, estresse e depressão devem ser entre 0 e 10.", "error")
            return redirect(url_for("admin"))

        media = (ansiedade + estresse + depressao) / 3
        nivel = calcular_nivel(media)

        conexao = get_conexao()
        cursor  = conexao.cursor()
        try:
            sql = """UPDATE usuarios
                     SET nome=%s, idade=%s, sexo=%s, ansiedade=%s, estresse=%s, depressao=%s, nivel=%s
                     WHERE id=%s"""
            cursor.execute(sql, (nome, idade, sexo, ansiedade, estresse, depressao, nivel, id_usuario))
            conexao.commit()
        finally:
            cursor.close()
            conexao.close()

        flash(f"Registro #{id_usuario} atualizado com sucesso!", "success")

    except (ValueError, KeyError):
        flash("Dados inválidos ao editar.", "error")

    return redirect(url_for("admin"))


@app.route("/admin/apagar", methods=["POST"])
def admin_apagar():
    try:
        id_usuario = int(request.form["id"])

        conexao = get_conexao()
        cursor  = conexao.cursor()
        try:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (id_usuario,))
            conexao.commit()
        finally:
            cursor.close()
            conexao.close()

        flash(f"Registro #{id_usuario} apagado.", "success")

    except (ValueError, KeyError):
        flash("ID inválido.", "error")

    return redirect(url_for("admin"))


@app.route("/admin/reorganizar-ids", methods=["POST"])
def admin_reorganizar_ids():
    conexao = get_conexao()
    cursor  = conexao.cursor()
    try:
        cursor.execute("SET @contador = 0;")
        cursor.execute("UPDATE usuarios SET id = (@contador := @contador + 1) ORDER BY id;")
        cursor.execute("ALTER TABLE usuarios AUTO_INCREMENT = 1;")
        conexao.commit()
        return jsonify({"ok": True, "msg": "IDs reorganizados com sucesso!"})
    except Exception as e:
        conexao.rollback()
        return jsonify({"ok": False, "msg": f"Erro: {str(e)}"})
    finally:
        cursor.close()
        conexao.close()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False)