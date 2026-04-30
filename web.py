import uuid
import os
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine
from core.database import Database
from core.production import ProductionManager
from core.tts import get_tts_manager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
CORS(app)


@app.after_request
def add_header(response):
    if request.path.startswith("/api/"):
        response.headers["Content-Type"] = "application/json"
    return response


# Global state
config, db = None, None
llm_handler = None
operations = None
conversation = None
transcribe_model = None  # ← New: global whisper model
production = None  # ← New: production manager
available_models = []


def get_ollama_models():
    import requests

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception as e:
        print(f"Error fetching models: {e}")
    return []


def init_app():
    global \
        config, \
        db, \
        llm_handler, \
        operations, \
        conversation, \
        transcribe_model, \
        production, \
        tts_manager, \
        available_models

    config, db = run_startup()
    llm_handler = LLMHandler(config)
    operations = Operation(db, llm_handler)
    conversation = ConversationEngine(db)
    production = ProductionManager(db)
    tts_manager = get_tts_manager({'cache_enabled': True})  # ← New

    available_models = get_ollama_models()

    # Check if Ollama is actually available (not just returning empty list)
    ollama_available = check_ollama(config["ollama"]["host"], config["ollama"]["port"])
    llamacpp_available = check_llama_cpp(config["llama_cpp"]["host"], config["llama_cpp"]["port"])

    # Read enabled flags from config to determine provider preference
    ollama_enabled = config.get("ollama", {}).get("enabled", True)
    llamacpp_enabled = config.get("llama_cpp", {}).get("enabled", False)

    # Respect user's config choice, fall back to availability
    if ollama_enabled and ollama_available and available_models:
        print(f"\nAvailable models: {', '.join(available_models)}")
        if config["ollama"]["model"] in available_models:
            print(f"Using: {config['ollama']['model']}")
        else:
            config["ollama"]["model"] = available_models[0]
            print(f"Switched to: {config['ollama']['model']}")
        llm_handler.set_provider("ollama")
    elif llamacpp_enabled and llamacpp_available:
        llm_handler.set_provider("llama_cpp")
        print("\nUsing: llama.cpp")
    elif ollama_available and available_models:
        print(f"\nAvailable models: {', '.join(available_models)}")
        if config["ollama"]["model"] in available_models:
            print(f"Using: {config['ollama']['model']}")
        else:
            config["ollama"]["model"] = available_models[0]
            print(f"Switched to: {config['ollama']['model']}")
        llm_handler.set_provider("ollama")
    elif llamacpp_available:
        llm_handler.set_provider("llama_cpp")
        print("\nUsing: llama.cpp")
    else:
        print("\n⚠ No LLM provider available")

    # Initialize Whisper model
    init_transcribe()


def init_transcribe():
    """Initialize Whisper model once at startup"""
    global transcribe_model
    try:
        from faster_whisper import WhisperModel
        transcribe_model = WhisperModel("base", device="cpu", compute_type="int8")
        print("✓ Whisper model loaded")
    except Exception as e:
        print(f"⚠ Whisper not available: {e}")
        transcribe_model = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    import traceback
    import time

    start = time.time()

    if not config:
        init_app()
        print("[CHAT] Re-initialized app")

    # FIX: Validate JSON input
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    print(f"[CHAT] Received: {user_message[:30]}")

    # FIX: Use per-user session instead of global
    if "session_id" not in session:
        session["session_id"] = conversation.start_session()
    current_session = session["session_id"]

    if user_message.startswith("/"):
        return handle_command(user_message)

    try:
        conversation.add_message(current_session, "user", user_message)

        context = conversation.get_conversation_summary(current_session)

        if not llm_handler.current_provider:
            # FIX: Better error message
            return jsonify({
                "error": "No LLM provider available",
                "available_models": available_models
            }), 503

        print(f"[CHAT] Provider: {llm_handler.current_provider}")
        print(f"[CHAT] Calling operations.process...")
        result = operations.process(
            user_message,
            {
                "context": context,
                "current_customer": conversation.get_context(current_session).get(
                    "current_customer_name"
                ),
            },
            output_format='html',
        )
        print(f"[CHAT] Result length: {len(result)}")

        conversation.add_message(current_session, "assistant", result)

        print(f"[CHAT] operations.process done in {time.time() - start:.1f}s")

        return jsonify({"response": result, "session": current_session[:8]})
    except Exception as e:
        import sys

        exc_type = sys.exc_info()[0].__name__
        exc_trace = "".join(traceback.format_exception(exc_type, e, e.__traceback__))[
            -500:
        ]
        print(f"[CHAT] Error: {exc_type}: {e}")

        return jsonify({"error": str(e), "type": exc_type, "trace": exc_trace}), 500


def handle_command(cmd):
    # FIX: Add db initialization check
    if not db:
        init_app()

    cmd = cmd[1:].lower()
    parts = cmd.split()
    action = parts[0] if parts else ""

    try:
        if action == "customers":
            rows = db.execute("SELECT * FROM customers LIMIT 10")
            return jsonify({"response": format_results(rows)})
        elif action == "items":
            rows = db.execute("SELECT * FROM items LIMIT 10")
            return jsonify({"response": format_results(rows)})
        elif action == "invoices":
            rows = db.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 10")
            return jsonify({"response": format_results(rows)})
        elif action == "switch":
            new = "llama_cpp" if llm_handler.current_provider == "ollama" else "ollama"
            msg = llm_handler.switch_provider(new)
            return jsonify({"response": msg})
        elif action == "model":
            # FIX: Show available models instead of items
            models = get_ollama_models()
            current = config.get("ollama", {}).get("model", "none")
            msg = f"Available models: {', '.join(models)}\nCurrent: {current}"
            return jsonify({"response": msg})
        else:
            return jsonify(
                {
                    "response": f"Unknown command: /{action}. Try /customers, /items, /invoices, /switch, /model"
                }
            )
    except Exception as e:
        return jsonify({"error": f"Command failed: {str(e)}"}), 500


@app.route("/api/customers", methods=["GET"])
def api_customers():
    # FIX: Initialize db if needed
    if not db:
        init_app()
    
    try:
        rows = db.execute("SELECT * FROM customers WHERE is_active = 1")
        return jsonify(rows or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/items", methods=["GET"])
def api_items():
    # FIX: Initialize db if needed
    if not db:
        init_app()
    
    try:
        rows = db.execute("SELECT * FROM items WHERE is_active = 1")
        return jsonify(rows or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/invoices", methods=["GET"])
def api_invoices():
    # FIX: Initialize db if needed
    if not db:
        init_app()
    
    try:
        rows = db.execute("""
            SELECT i.*, c.customer_name 
            FROM invoices i 
            LEFT JOIN customers c ON i.customer_id = c.id 
            ORDER BY i.created_at DESC
        """)
        return jsonify(rows or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/invoice/<int:invoice_id>", methods=["GET"])
def api_invoice_detail(invoice_id):
    # FIX: Initialize db if needed
    if not db:
        init_app()
    
    try:
        invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        # FIX: Check if empty list
        if not invoice or len(invoice) == 0:
            return jsonify({"error": "Not found"}), 404

        items = db.execute(
            """
            SELECT ii.*, i.item_name, i.item_code
            FROM invoice_items ii
            JOIN items i ON ii.item_id = i.id
            WHERE ii.invoice_id = ?
        """,
            (invoice_id,),
        )

        return jsonify({"invoice": invoice[0], "items": items or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/invoice/<int:invoice_id>/pdf", methods=["GET"])
def api_invoice_pdf(invoice_id):
    from utils.invoice_generator import generate_invoice_pdf
    import os

    # FIX: Initialize db if needed
    if not db:
        init_app()
    
    try:
        invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        # FIX: Check if empty list
        if not invoice or len(invoice) == 0:
            return jsonify({"error": "Not found"}), 404

        inv = invoice[0]
        items = db.execute(
            """
            SELECT ii.*, i.item_name
            FROM invoice_items ii
            JOIN items i ON ii.item_id = i.id
            WHERE ii.invoice_id = ?
        """,
            (invoice_id,),
        )

        items_list = [
            {
                "item_name": i["item_name"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "amount": i["amount"],
            }
            for i in (items or [])
        ]

        os.makedirs("invoices", exist_ok=True)
        pdf_path = f"invoices/{inv['invoice_no']}.pdf"

        generate_invoice_pdf(
            inv["invoice_no"],
            inv["customer_name"],
            items_list,
            inv["subtotal"],
            inv["tax_rate"],
            inv["tax_amount"],
            inv["total_amount"],
            inv["due_date"],
            pdf_path,
        )

        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models", methods=["GET"])
def api_models():
    global config
    if not config:
        init_app()
    try:
        models = get_ollama_models()
        current_model = config["ollama"]["model"] if config else "gemma3:270m"
        return jsonify({"models": models, "current": current_model})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/model/<path:model_name>", methods=["POST"])
def api_set_model(model_name):
    if not config:
        init_app()
    
    try:
        available = get_ollama_models()
        if model_name not in available:
            return jsonify({"error": f"Model {model_name} not available"}), 400

        config["ollama"]["model"] = model_name
        if llm_handler:
            llm_handler.config["ollama"]["model"] = model_name
        
        return jsonify({"success": True, "model": model_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_results(rows):
    if not rows:
        return "No results."
    if len(rows) == 1:
        return "\n".join(f"{k}: {v}" for k, v in rows[0].items())

    headers = list(rows[0].keys())
    header_line = " | ".join(headers)
    lines = [header_line, "-" * len(header_line)]
    for row in rows:
        lines.append(" | ".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines)


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    global transcribe_model
    import tempfile
    import os

    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    # FIX: Check if transcribe model is available
    if transcribe_model is None:
        return jsonify({"error": "Transcription service not available"}), 503

    audio_file = request.files["audio"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp)
        tmp_path = tmp.name

    try:
        segments, info = transcribe_model.transcribe(tmp_path, beam_size=5)
        text = " ".join(segment.text for segment in segments)
        return jsonify({"text": text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


@app.route("/api/voice/chat", methods=["POST"])
def voice_chat():
    """Voice chat endpoint - accepts audio, returns audio response."""
    import tempfile
    import os
    import io
    import soundfile as sf
    
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400
    
    if transcribe_model is None:
        return jsonify({"error": "Transcription service not available"}), 503
    
    audio_file = request.files["audio"]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp)
        tmp_path = tmp.name
    
    try:
        # Step 1: Transcribe audio to text
        segments, info = transcribe_model.transcribe(tmp_path, beam_size=5)
        user_text = " ".join(segment.text for segment in segments).strip()
        
        if not user_text:
            return jsonify({"error": "Could not transcribe audio"}), 400
        
        print(f"[VOICE] User said: {user_text[:50]}...")
        
        # Step 2: Process with LLM
        session_id = session.get("session_id")
        if not session_id:
            session["session_id"] = conversation.start_session()
            session_id = session["session_id"]
        
        conversation.add_message(session_id, "user", user_text)
        context = conversation.get_conversation_summary(session_id)
        
        result = operations.process(
            user_text,
            {
                "context": context,
                "current_customer": conversation.get_context(session_id).get(
                    "current_customer_name"
                ),
            },
            output_format='text',
        )
        
        conversation.add_message(session_id, "assistant", result)
        
        # Step 3: Convert text to speech using local TTS
        tts_audio_path = None
        tts_success = False
        
        if tts_manager.is_available():
            tts_result = tts_manager.synthesize(result, use_cache=True)
            
            if tts_result['success']:
                tts_audio_path = tts_result['audio_path']
                tts_success = True
                print(f"[VOICE] TTS synthesized: {tts_result['duration']:.2f}s")
        
        # Prepare response
        response_data = {
            "text": result,
            "transcribed": user_text,
            "session": session_id[:8],
            "tts_available": tts_success
        }
        
        # If TTS succeeded, return audio file
        if tts_success and tts_audio_path:
            with open(tts_audio_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Clean up temp audio file
            try:
                os.unlink(tts_audio_path)
            except:
                pass
            
            # Return as multipart response or just JSON with audio data
            import base64
            response_data["audio"] = base64.b64encode(audio_bytes).decode('utf-8')
            response_data["audio_format"] = "wav"
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


@app.route("/api/voice/config", methods=["GET"])
def voice_config():
    """Get voice agent configuration and capabilities."""
    tts_info = tts_manager.get_info()
    
    return jsonify({
        "stt_available": transcribe_model is not None,
        "stt_model": "faster-whisper-base",
        "tts_available": tts_info['available'],
        "tts_engine": tts_info['engine'],
        "tts_type": tts_info['type'],
        "tts_voices": tts_info['voices'],
        "recommended_tts": ["local (espeak-ng)", "elevenlabs", "openai"],
        "latency_target_ms": 800,
        "features": {
            "barge_in": True,
            "streaming": True,
            "noise_reduction": True
        }
    })


@app.route("/api/tts/synthesize", methods=["POST"])
def api_tts_synthesize():
    """Synthesize text to speech."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    voice = data.get("voice", None)
    
    if not text:
        return jsonify({"error": "text required"}), 400
    
    if not tts_manager.is_available():
        return jsonify({"error": "TTS not available"}), 503
    
    try:
        result = tts_manager.synthesize(text, use_cache=data.get("use_cache", True))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts/info", methods=["GET"])
def api_tts_info():
    """Get TTS system information."""
    return jsonify(tts_manager.get_info())


@app.route("/api/production/bom/<int:bom_id>", methods=["GET"])
def api_bom_detail(bom_id):
    """Get BOM details."""
    try:
        bom_data = production.get_bom(bom_id=bom_id)
        if not bom_data:
            return jsonify({"error": "BOM not found"}), 404
        return jsonify(bom_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production/bom/<int:bom_id>/cost", methods=["GET"])
def api_bom_cost(bom_id):
    """Calculate BOM cost."""
    try:
        cost_data = production.calculate_bom_cost(bom_id)
        return jsonify(cost_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production/feasibility", methods=["POST"])
def api_production_feasibility():
    """Check production feasibility."""
    data = request.get_json(silent=True) or {}
    bom_id = data.get("bom_id")
    quantity = data.get("quantity", 1)
    
    if not bom_id:
        return jsonify({"error": "bom_id required"}), 400
    
    try:
        feasibility = production.check_production_feasibility(bom_id, quantity)
        return jsonify(feasibility)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production/work-order", methods=["POST"])
def api_create_work_order():
    """Create a work order."""
    data = request.get_json(silent=True) or {}
    bom_id = data.get("bom_id")
    quantity = data.get("quantity", 1)
    warehouse_id = data.get("warehouse_id", 1)
    notes = data.get("notes", "")
    
    if not bom_id:
        return jsonify({"error": "bom_id required"}), 400
    
    try:
        wo = production.create_work_order(bom_id, quantity, warehouse_id, notes)
        return jsonify(wo)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production/work-order/<int:wo_id>/complete", methods=["POST"])
def api_complete_work_order(wo_id):
    """Complete a work order."""
    try:
        result = production.complete_work_order(wo_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/production/summary", methods=["GET"])
def api_production_summary():
    """Get production summary."""
    try:
        summary = production.get_production_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_app()
    print("\n🌐 Web UI: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
