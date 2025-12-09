@echo off
REM makefsdata_py.bat - Wrapper para executar o script Python makefsdata.py
REM
REM Projeto : mk-lwip-httpd-fs
REM Proposito: Converter arvore de arquivos web em fsdata.c (httpd lwIP) via Python
REM Autor   : Carlos Delfino
REM Data    : 2025-12-09
REM Dependencias: Python 3; ambiente virtual opcional em
REM              - MakeFSdataProjPlusExample\venv
REM              - venv-mk-lwip-httpd-fs\ na raiz do projeto
REM
REM Uso:
REM   scripts\makefsdata_py.bat [targetdir] [opcoes]
REM Os parametros sao repassados diretamente ao makefsdata.py.

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
REM SUBPROJ_DIR deve apontar para a raiz "makefs" (já é PROJECT_ROOT)
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

"%PYTHON%" "%SUBPROJ_DIR%\makefsdata\makefsdata.py" %*

endlocal
