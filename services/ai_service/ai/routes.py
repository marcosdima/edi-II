from flask import Blueprint, jsonify, request

from .services import AIService

ai_bp = Blueprint("ai", __name__)


def get_proxy_metadata():
    """Extracts reverse proxy headers sent by Nginx for auditing demonstration."""
    return {
        "client_ip": request.headers.get("X-Real-IP", request.remote_addr),
        "forwarded_proto": request.headers.get("X-Forwarded-Proto", "http"),
        "country": request.headers.get("X-Country-Code", "UNKNOWN"),
    }


@ai_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker and Nginx reverse proxy."""
    info = AIService.get_service_info()
    return (
        jsonify(
            {
                "service": "ai-service",
                "status": "healthy",
                "provider": info["provider"],
                "api_key_configured": info["api_key_configured"],
                "offline_fallback_enabled": True,
            }
        ),
        200,
    )


@ai_bp.route("/info", methods=["GET"])
def service_info():
    """Returns provider configurations, model in use, and fallback status."""
    return (
        jsonify(
            {
                "service": "ai-service",
                "configuration": AIService.get_service_info(),
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        200,
    )


@ai_bp.route("/generate", methods=["POST"])
def generate_completion():
    """
    Generates an AI text completion via Groq or OpenRouter.
    Payload:
      {
        "prompt": "Explain reverse proxies in 2 sentences",
        "system_prompt": "You are a concise sysadmin assistant",
        "model": "optional model override",
        "temperature": 0.7
      }
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "'prompt' field is required."}), 400

    system_prompt = data.get("system_prompt")
    model = data.get("model")
    try:
        temperature = float(data.get("temperature", 0.7))
    except (ValueError, TypeError):
        return jsonify({"error": "'temperature' must be a numeric value."}), 400

    ai_response = AIService.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )

    return (
        jsonify(
            {
                "status": "success",
                "response": ai_response.to_dict(),
                "proxy_metadata": get_proxy_metadata(),
            }
        ),
        200,
    )
