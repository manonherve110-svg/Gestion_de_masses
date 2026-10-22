import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from mediator import Mediator

app = Flask(__name__)
CORS(app)

try:
    mediator = Mediator()
except Exception as e:
    print(f"Erreur d'initialisation du médiateur: {e}", file=sys.stderr)
    mediator = None

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def _mediator_required():
    if not mediator:
        return jsonify({
            "error": "Médiateur non initialisé. Lancez : python3 mediator.py --setup puis python3 scripts/api.py"
        }), 500
    return None


@app.route("/api/search", methods=["GET"])
def search():
    err = _mediator_required()
    if err:
        return err

    query = request.args.get("q", "")
    operator = request.args.get("operator", "AND")

    if not query:
        return jsonify({"error": "Paramètre 'q' (requête) manquant."}), 400

    return jsonify(mediator.resolve_query(query, operator))


@app.route("/api/suggest", methods=["GET"])
def suggest():
    err = _mediator_required()
    if err:
        return err

    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    return jsonify(mediator.suggest_symptoms(query))


@app.route("/api/stats", methods=["GET"])
def stats():
    err = _mediator_required()
    if err:
        return err
    return jsonify(mediator.get_source_statistics())


@app.route("/api/mapping-stats", methods=["GET"])
def mapping_stats():
    err = _mediator_required()
    if err:
        return err
    return jsonify(mediator.get_mapping_statistics())


@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    print("Démarrage de l'API sur http://127.0.0.1:5000", file=sys.stderr)
    app.run(host="127.0.0.1", port=5000, debug=True)
