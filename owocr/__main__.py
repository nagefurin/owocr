import multiprocessing
import sys
import os

def main():
    from owocr.paths import configure_portable_caches
    configure_portable_caches()

    if not getattr(sys, 'frozen', False):
        original_stderr_fd = os.dup(sys.stderr.fileno())
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())
        sys.stderr = os.fdopen(original_stderr_fd, 'w', encoding='utf-8')
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004) # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    multiprocessing.set_start_method('spawn')
    if sys.platform == 'darwin':
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    elif sys.platform == 'win32':
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    from owocr.run import run
    run()

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        multiprocessing.freeze_support()
        if os.environ.get('OWOCR_PACKAGED_IMPORT_SMOKE_TEST') == '1':
            import traceback
            from pathlib import Path
            smoke_dir = Path(sys.executable).resolve().parent
            test_log = smoke_dir / 'owocr-import-smoke-test.log'
            test_started = smoke_dir / 'owocr-import-smoke-test.started'
            test_ok = smoke_dir / 'owocr-import-smoke-test.ok'
            test_started.write_text('started', encoding='utf-8')
            try:
                from transformers import AutoImageProcessor, ViTImageProcessor
                from manga_ocr import MangaOcr
                from hayai_ocr import HayaiOcr
            except Exception:
                test_log.write_text(traceback.format_exc(), encoding='utf-8')
                sys.exit(1)
            else:
                test_ok.write_text('OK', encoding='utf-8')
                sys.exit(0)
    main()
