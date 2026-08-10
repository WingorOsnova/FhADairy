# Fachabi Diary

Локальное desktop-приложение для еженедельных Berichtsbogen по Brandenburg FOSFHRV Formblatt 9.

## Возможности MVP

- профиль практики с данными Lysenko / Kostiantyn / Garamantis GmbH;
- первичная настройка профиля с Arbeitswoche и проверкой обязательных полей;
- создание, редактирование и удаление недельных отчётов;
- автосохранение открытого отчёта после изменений и перед переключением недель;
- статусы `Entwurf`, `Bereit`, `Gedruckt`, `Unterschrieben`;
- 7 дневных строк с датой, часами и текстом деятельности;
- автоматическая сумма часов за неделю;
- настройка рабочей недели и автозаполнение выходных;
- локальная KI-Hilfe для очистки Tagesnotiz, Wochennotiz и более формального текста;
- экспорт одного отчёта в официальный PDF;
- экспорт всех заполненных отчётов в один PDF;
- диалог результата экспорта с открытием PDF и показом файла в Finder;
- последний PDF-путь сохраняется у недельного отчёта;
- в отчёте показывается последний PDF-Export с датой, именем файла и быстрыми действиями;
- сохранённый PDF можно открыть или показать в Finder через меню `Weitere`;
- успешный PDF-Export setzt einen Entwurf automatisch auf `Bereit`;
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

## Сборка macOS `.app`

```bash
cd /Users/lysenko-kostiantyn/IT/FhADairy
venv/bin/python -m pip install -e ".[dev]"
bash scripts/build_macos_app.sh
open "dist/Fachabi Diary.app"
```

Скрипт встраивает `assets/formblatt9.pdf` внутрь `.app`, поэтому запуск не зависит от текущей папки терминала.

## Упаковка релиза для GitHub

```bash
bash scripts/build_macos_app.sh
bash scripts/package_macos_release.sh
```

Готовые файлы появятся в `dist/release/`:

```text
Fachabi-Diary-0.1.0-macOS-arm64.zip
Fachabi-Diary-0.1.0-macOS-arm64.dmg
```

Пока приложение не подписано Apple Developer ID, macOS может показывать предупреждение Gatekeeper при первом запуске.

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
