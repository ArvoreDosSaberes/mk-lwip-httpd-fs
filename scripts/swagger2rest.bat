@echo off
REM swagger2rest.bat - Wrapper para executar o script Python swagger2rest.py
REM
REM Projeto : STM32-F429zi-http
REM Proposito: Gerar descricoes de endpoints REST (headers .h/.c) a partir de
REM            um arquivo Swagger/OpenAPI em JSON.
REM
REM Uso basico:
REM   scripts\swagger2rest.bat <swagger_dir> -o <dest_header> -v <version>
REM
REM Os parametros sao repassados diretamente ao swagger2rest.py.

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
REM SUBPROJ_DIR deve apontar para a raiz "makefs" (ja e PROJECT_ROOT)
set "SUBPROJ_DIR=%PROJECT_ROOT%"

set "PYTHON="

if exist "%SUBPROJ_DIR%\venv\Scripts\python.exe" (
  set "PYTHON=%SUBPROJ_DIR%\venv\Scripts\python.exe"
) else if exist "%PROJECT_ROOT%\venv-mk-lwip-httpd-fs\Scripts\python.exe" (
  set "PYTHON=%PROJECT_ROOT%\venv-mk-lwip-httpd-fs\Scripts\python.exe"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYTHON=python"
  ) else (
    echo Erro: Python nao encontrado no sistema nem em ambientes virtuais conhecidos.
    exit /b 1
  )
)

"%PYTHON%" "%SUBPROJ_DIR%\swagger\swagger2rest.py" %*

endlocal
