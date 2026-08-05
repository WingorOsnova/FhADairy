# Fachabi Diary

Локальное desktop-приложение для еженедельных Berichtsbogen по Brandenburg FOSFHRV Formblatt 9.

## Возможности MVP

- профиль практики с данными Lysenko / Kostiantyn / Garamantis GmbH;
- создание, редактирование и удаление недельных отчётов;
- статусы `Entwurf`, `Bereit`, `Gedruckt`, `Unterschrieben`;
- 7 дневных строк с датой, часами и текстом деятельности;
- автоматическая сумма часов за неделю;
- локальная KI-Hilfe для очистки Tagesnotiz, Wochennotiz и более формального текста;
- экспорт одного отчёта в официальный PDF;
- экспорт всех заполненных отчётов в один PDF;
- подписи и печать в PDF остаются пустыми.

## Установка на macOS

```bash
cd /Users/lysenko-kostiantyn/IT/FhADairy
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m fachabi_diary
```

Если `python3.12` не установлен, можно попробовать `python3`, если он версии 3.12 или новее:

```bash
python3 --version
```

## Установка на Windows

```powershell
cd путь\к\FhADairy
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m fachabi_diary
```

Если PowerShell запрещает активацию окружения:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Проверка

```bash
pytest
```

## PDF-шаблон

Официальный шаблон должен лежать здесь:

```text
assets/formblatt9.pdf
```

В этом репозитории он уже скопирован из `Formblatt_9_FOSFHRV.pdf`.

## Где хранятся данные

Приложение использует SQLite в системной папке данных Qt (`QStandardPaths.AppDataLocation`). На macOS это обычно путь внутри `~/Library/Application Support/`.

## Ограничения MVP

- нет облачной синхронизации, аккаунтов и сетевых функций;
- нет подключённой онлайн-AI-модели: KI-Hilfe работает локально по простым правилам и не отправляет данные в сеть;
- нет установщика `.dmg` или `.exe`;
- PDF-позиции подобраны для Formblatt 9 и могут потребовать тонкой ручной подгонки после печатной проверки.
