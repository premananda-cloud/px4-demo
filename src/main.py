import asyncio
import sys
from pathlib import Path

# Add src to path if needed
if str(Path(__file__).parent) not in sys.path:
    sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI
import uvicorn
from src.api.routes import router
from src.services.inference import get_inference_service
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SmolLM2 API", version="1.0.0")
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    logger.info("Loading SmolLM2 model...")
    try:
        service = get_inference_service()
        # Pre-load the model
        service.model, service.tokenizer, service.device = service.loader.get_model()
        logger.info("Model loaded and ready!")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

def run_terminal():
    """Run interactive terminal mode"""
    logger.info("Starting terminal interface...")
    service = get_inference_service()

    print("\n" + "="*50)
    print(" SmolLM2 Terminal Interface")
    print("="*50)
    print("Type 'exit' or 'quit' to end session")
    print("Type 'clear' to clear the screen")
    print("Type 'system: <prompt>' to set system prompt")
    print("-"*50)

    system_prompt = "You are a helpful assistant."
    conversation_history = []

    while True:
        try:
            # Get user input
            user_input = input("\n> ").strip()

            # Check special commands
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            elif user_input.lower() == 'clear':
                import os
                os.system('clear' if os.name == 'posix' else 'cls')
                continue
            elif user_input.lower().startswith('system:'):
                system_prompt = user_input[7:].strip()
                print(f"System prompt updated: {system_prompt}")
                continue

            if not user_input:
                continue

            # Generate response
            result = service.generate_response(
                user_input=user_input,
                system_prompt=system_prompt
            )

            if result["success"]:
                print(f"\nAssistant: {result['response']}")
                conversation_history.append(("user", user_input))
                conversation_history.append(("assistant", result['response']))
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")

def main():
    parser = argparse.ArgumentParser(description="SmolLM2 Runner")
    parser.add_argument("--mode", choices=["api", "terminal"], default="api",
                       help="Run mode: api or terminal")
    parser.add_argument("--host", default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")

    args = parser.parse_args()

    if args.mode == "terminal":
        run_terminal()
    else:
        # Run API server
        uvicorn.run(
            "src.main:app",
            host=args.host,
            port=args.port,
            reload=False
        )

if __name__ == "__main__":
    main()
