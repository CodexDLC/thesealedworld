from pathlib import Path

from codex_core.dev.static_compiler.compiler import StaticCompiler
from loguru import logger

# Пути относительно этого файла
CORE_DIR = Path(__file__).parent
FRONTEND_DIR = CORE_DIR.parent
STATIC_DIR = FRONTEND_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

CONFIG_PATH = CSS_DIR / "compiler_config.json"


def compile_static_assets(minify: bool = False) -> bool:
    """
    Компилирует CSS и JS активы фронтенда.
    Используется в lifespan приложения FastAPI или как отдельный скрипт.
    """
    if not CONFIG_PATH.exists():
        logger.warning(f"Static compiler config not found at {CONFIG_PATH}. Skipping compilation.")
        return False

    logger.info("🎨 Compiling static assets...")

    # Инициализируем компилятор из codex-core
    compiler = StaticCompiler(
        minify=minify,
        remove_comments=not minify,
    )

    # Запускаем сборку
    # Передаем явные пути к папкам css и js, чтобы компилятор знал, где искать исходники
    success = compiler.compile_from_config(
        config=CONFIG_PATH,
        css_dir=CSS_DIR,
        js_dir=JS_DIR,
    )

    if success:
        logger.info("✅ Static assets compiled successfully")
    else:
        logger.error("❌ Static assets compilation failed")

    return success


if __name__ == "__main__":
    # Позволяет запускать компиляцию вручную: python -m src.frontend.core.static
    compile_static_assets(minify=False)
