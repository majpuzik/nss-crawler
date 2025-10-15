#!/usr/bin/env python3
"""
web_app.py
Flask webové GUI pro prohlížení databáze rozhodnutí NSS
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import logging
from pathlib import Path
from config import DB_PATH
from job_manager import job_manager
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


def get_db():
    """Získat databázové připojení"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Hlavní stránka"""
    return render_template('index.html')


@app.route('/api/stats')
def api_stats():
    """API endpoint pro statistiky"""
    conn = get_db()
    cursor = conn.cursor()

    # Celkové statistiky
    cursor.execute('SELECT COUNT(*) FROM decisions')
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE full_text IS NOT NULL AND length(full_text) > 100")
    with_text = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE (full_text IS NULL OR full_text = '' OR length(full_text) <= 100)")
    needs_text = cursor.fetchone()[0]

    # Podle roku
    cursor.execute("""
        SELECT
            strftime('%Y', date) as rok,
            COUNT(*) as pocet
        FROM decisions
        WHERE date IS NOT NULL
        GROUP BY rok
        ORDER BY rok DESC
    """)
    by_year = [{'year': row[0], 'count': row[1]} for row in cursor.fetchall()]

    # Podle tématu
    cursor.execute("""
        SELECT
            CASE
                WHEN metadata LIKE '%dotace%' THEN 'Dotace'
                WHEN metadata LIKE '%zelená plocha%' THEN 'Zelená plocha'
                ELSE 'Ostatní'
            END as tema,
            COUNT(*) as pocet
        FROM decisions
        WHERE metadata IS NOT NULL
        GROUP BY tema
        ORDER BY pocet DESC
    """)
    by_topic = [{'topic': row[0], 'count': row[1]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        'total': total,
        'with_text': with_text,
        'needs_text': needs_text,
        'by_year': by_year,
        'by_topic': by_topic
    })


@app.route('/api/decisions')
def api_decisions():
    """API endpoint pro seznam rozhodnutí"""
    conn = get_db()
    cursor = conn.cursor()

    # Parametry
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    year = request.args.get('year', '')
    has_text = request.args.get('has_text', '')

    offset = (page - 1) * per_page

    # Sestavit query
    where_clauses = []
    params = []

    if search:
        where_clauses.append("(ecli LIKE ? OR title LIKE ?)")
        params.extend([f'%{search}%', f'%{search}%'])

    if year:
        where_clauses.append("strftime('%Y', date) = ?")
        params.append(year)

    if has_text == 'yes':
        where_clauses.append("(full_text IS NOT NULL AND length(full_text) > 100)")
    elif has_text == 'no':
        where_clauses.append("(full_text IS NULL OR full_text = '' OR length(full_text) <= 100)")

    where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

    # Celkový počet
    cursor.execute(f'SELECT COUNT(*) FROM decisions WHERE {where_sql}', params)
    total = cursor.fetchone()[0]

    # Data
    cursor.execute(f"""
        SELECT
            id, ecli, title, date, url,
            CASE WHEN full_text IS NOT NULL AND length(full_text) > 100 THEN 1 ELSE 0 END as has_text,
            needs_fulltext,
            metadata
        FROM decisions
        WHERE {where_sql}
        ORDER BY date DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    decisions = []
    for row in cursor.fetchall():
        metadata = json.loads(row[7]) if row[7] else {}
        decisions.append({
            'id': row[0],
            'ecli': row[1],
            'title': row[2],
            'date': row[3],
            'url': row[4],
            'has_text': bool(row[5]),
            'needs_fulltext': bool(row[6]),
            'metadata': metadata
        })

    conn.close()

    return jsonify({
        'decisions': decisions,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })


@app.route('/api/decision/<int:decision_id>')
def api_decision_detail(decision_id):
    """API endpoint pro detail rozhodnutí"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, ecli, title, date, url, full_text, keywords, needs_fulltext, metadata
        FROM decisions
        WHERE id = ?
    """, (decision_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Not found'}), 404

    metadata = json.loads(row[8]) if row[8] else {}

    return jsonify({
        'id': row[0],
        'ecli': row[1],
        'title': row[2],
        'date': row[3],
        'url': row[4],
        'full_text': row[5],
        'keywords': row[6].split(',') if row[6] else [],
        'needs_fulltext': bool(row[7]),
        'metadata': metadata
    })


@app.route('/api/search')
def api_fulltext_search():
    """API endpoint pro fulltextové vyhledávání"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 50))

    if not query:
        return jsonify({'results': [], 'query': query})

    conn = get_db()
    cursor = conn.cursor()

    # FTS5 vyhledávání
    cursor.execute("""
        SELECT d.id, d.ecli, d.title, d.date,
               CASE WHEN d.full_text IS NOT NULL AND length(d.full_text) > 100 THEN 1 ELSE 0 END as has_text
        FROM decisions d
        JOIN decisions_fts fts ON d.id = fts.rowid
        WHERE decisions_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'ecli': row[1],
            'title': row[2],
            'date': row[3],
            'has_text': bool(row[4])
        })

    conn.close()

    return jsonify({
        'results': results,
        'query': query,
        'count': len(results)
    })


@app.route('/api/mark_for_download', methods=['POST'])
def api_mark_for_download():
    """API endpoint pro označení rozhodnutí k stažení"""
    data = request.get_json()
    decision_ids = data.get('decision_ids', [])

    if not decision_ids:
        return jsonify({'error': 'No decision IDs provided'}), 400

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(decision_ids))
    cursor.execute(f"""
        UPDATE decisions
        SET needs_fulltext = 1
        WHERE id IN ({placeholders})
    """, decision_ids)

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': updated})


@app.route('/api/search_nss', methods=['POST'])
def api_search_nss():
    """API endpoint pro vyhledávání v NSS sbírce"""
    data = request.get_json()
    keywords = data.get('keywords', [])
    limit = data.get('limit', 10)

    if not keywords:
        return jsonify({'error': 'No keywords provided'}), 400

    # Vytvořit job
    job = job_manager.create_job('search_nss', f'Vyhledávání: {", ".join(keywords)}')

    # Spustit vyhledávání na pozadí
    from downloader import NSSSbirkaDownloader
    import threading

    def background_search():
        downloader = NSSSbirkaDownloader()
        try:
            decisions = downloader.search_and_download(keywords, limit, job)
            job.complete()
            logger.info(f"✅ Background search completed: {len(decisions)} decisions")
        except Exception as e:
            job.fail(str(e))
            logger.error(f"❌ Background search failed: {e}")
        finally:
            downloader.close()

    thread = threading.Thread(target=background_search)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': f'Vyhledávání spuštěno na pozadí pro: {", ".join(keywords)}',
        'keywords': keywords,
        'limit': limit,
        'job_id': job.job_id
    })


@app.route('/api/download_marked')
def api_download_marked():
    """API endpoint pro stažení označených rozhodnutí"""
    conn = get_db()
    cursor = conn.cursor()

    # Získat označená rozhodnutí
    cursor.execute("""
        SELECT id, ecli, metadata
        FROM decisions
        WHERE needs_fulltext = 1
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'success': True, 'message': 'Žádná rozhodnutí k stažení'})

    # Spustit stahování na pozadí
    from downloader import NSSSbirkaDownloader
    import threading
    import json

    def background_download():
        downloader = NSSSbirkaDownloader()
        try:
            downloaded = 0
            for row in rows:
                metadata = json.loads(row[2]) if row[2] else {}
                spisova_znacka = metadata.get('spisova_znacka')

                if spisova_znacka:
                    decision = downloader.download_by_spisova_znacka(spisova_znacka)
                    if decision:
                        downloaded += 1

            logger.info(f"✅ Background download completed: {downloaded}/{len(rows)} decisions")
        finally:
            downloader.close()

    thread = threading.Thread(target=background_download)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': f'Stahování spuštěno na pozadí pro {len(rows)} rozhodnutí',
        'total': len(rows)
    })


@app.route('/api/jobs')
def api_jobs():
    """API endpoint pro seznam všech jobů"""
    jobs = job_manager.get_all_jobs()
    return jsonify({
        'jobs': [j.to_dict() for j in jobs]
    })


@app.route('/api/job/<job_id>')
def api_job_status(job_id):
    """API endpoint pro status konkrétního jobu"""
    job = job_manager.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(job.to_dict())


@app.route('/api/job/<job_id>/cancel', methods=['POST'])
def api_cancel_job(job_id):
    """API endpoint pro zrušení jobu"""
    success = job_manager.cancel_job(job_id)

    if not success:
        return jsonify({'error': 'Cannot cancel job'}), 400

    return jsonify({'success': True, 'message': 'Job cancelled'})


@app.route('/api/download_all_without_text', methods=['POST'])
def api_download_all_without_text():
    """API endpoint pro stažení všech rozhodnutí bez textu"""
    data = request.get_json()
    limit = data.get('limit', 50)

    if limit > 200:
        return jsonify({'error': 'Limit nesmí být větší než 200'}), 400

    # Vytvořit job
    job = job_manager.create_job('download_all', f'Hromadné stahování {limit} rozhodnutí')

    # Získat rozhodnutí bez textu s metadaty
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url, ecli, metadata
        FROM decisions
        WHERE (full_text IS NULL OR full_text = '' OR length(full_text) <= 100)
        AND url IS NOT NULL AND url != ''
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'success': True, 'message': 'Žádná rozhodnutí k stažení'}), 200

    # Spustit stahování na pozadí
    from downloader import NSSSbirkaDownloader
    import threading

    def background_download():
        downloader = NSSSbirkaDownloader()
        try:
            downloaded = 0
            for i, row in enumerate(rows, 1):
                # Kontrola zrušení
                if job.cancel_requested:
                    logger.info("❌ Hromadné stahování zrušeno uživatelem")
                    job.status = "cancelled"
                    job.complete()
                    downloader.close()
                    return

                decision_id, url, ecli, metadata_json = row[0], row[1], row[2], row[3]

                # Extrahovat spisovou značku z metadata
                spisova_znacka = None
                if metadata_json:
                    try:
                        metadata = json.loads(metadata_json)
                        spisova_znacka = metadata.get('spisova_znacka')
                    except:
                        pass

                # Pokud nemáme spisovou značku, zkusit z ECLI nebo URL
                if not spisova_znacka:
                    # Z URL: https://vyhledavac.nssoud.cz/?spisova_znacka=5 As 211/2025
                    # nebo: https://vyhledavac.nssoud.cz/?q=3+Afs+257/2024
                    import re
                    if 'spisova_znacka=' in url:
                        match = re.search(r'spisova_znacka=([^&]+)', url)
                        if match:
                            spisova_znacka = match.group(1).replace('+', ' ')
                    elif '?q=' in url:
                        match = re.search(r'\?q=([^&]+)', url)
                        if match:
                            spisova_znacka = match.group(1).replace('+', ' ')

                if not spisova_znacka:
                    logger.warning(f"⚠️  [{i}/{len(rows)}] Nelze zjistit spisovou značku pro #{decision_id}")
                    continue

                job.update(i, len(rows), f"Stahuji {spisova_znacka}...")

                try:
                    import time
                    import urllib.parse
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC

                    # Vyhledat v NSS sbírce
                    encoded_query = urllib.parse.quote(spisova_znacka)
                    search_url = f"http://sbirka.nssoud.cz/cz/vyhledavani?q={encoded_query}"

                    logger.info(f"   [{i}/{len(rows)}] Hledám v NSS sbírce: {spisova_znacka}")
                    downloader.driver.get(search_url)
                    time.sleep(3)

                    # Počkat na výsledky
                    try:
                        results = WebDriverWait(downloader.driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".list-item"))
                        )

                        if not results:
                            logger.warning(f"⚠️  [{i}/{len(rows)}] Žádné výsledky pro {spisova_znacka}")
                            continue

                        # Otevřít první výsledek
                        link = results[0].find_element(By.CSS_SELECTOR, "a")
                        detail_url = link.get_attribute("href")

                        downloader.driver.get(detail_url)
                        time.sleep(2)

                        # Extrahovat text
                        body = downloader.driver.find_element(By.TAG_NAME, "body")
                        full_text = body.text

                        if len(full_text) > 500:
                            # Aktualizovat v databázi
                            conn = sqlite3.connect(str(DB_PATH))
                            cursor = conn.cursor()
                            cursor.execute("UPDATE decisions SET full_text = ?, url = ? WHERE id = ?",
                                         (full_text, detail_url, decision_id))
                            conn.commit()
                            conn.close()

                            job.add_result({'id': decision_id, 'text_length': len(full_text)})
                            downloaded += 1
                            logger.info(f"✅ [{i}/{len(rows)}] Staženo #{decision_id}: {len(full_text)} znaků")
                        else:
                            logger.warning(f"⚠️  [{i}/{len(rows)}] Text #{decision_id} je příliš krátký")

                    except Exception as e:
                        logger.warning(f"⚠️  [{i}/{len(rows)}] Nenalezeno v NSS sbírce: {e}")

                except Exception as e:
                    logger.error(f"❌ [{i}/{len(rows)}] Chyba u #{decision_id}: {e}")
                    continue

            job.complete()
            logger.info(f"✅ Hromadné stahování dokončeno: {downloaded}/{len(rows)} rozhodnutí")

        except Exception as e:
            job.fail(str(e))
            logger.error(f"❌ Chyba při hromadném stahování: {e}")
        finally:
            downloader.close()

    thread = threading.Thread(target=background_download)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': f'Zahájeno stahování {len(rows)} rozhodnutí',
        'job_id': job.job_id,
        'count': len(rows)
    })


@app.route('/api/download_single', methods=['POST'])
def api_download_single():
    """API endpoint pro stažení jednoho rozhodnutí"""
    data = request.get_json()
    url = data.get('url')
    decision_id = data.get('decision_id')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Vytvořit job
    job = job_manager.create_job('download_single', f'Stahování rozhodnutí #{decision_id}')

    # Spustit stahování na pozadí
    from downloader import NSSSbirkaDownloader
    import threading

    def background_download():
        downloader = NSSSbirkaDownloader()
        try:
            job.update(0, 1, "Otevírám stránku...")

            # Otevřít URL
            downloader.driver.get(url)
            import time
            time.sleep(2)

            job.update(1, 1, "Stahuji text...")

            # Extrahovat text
            body = downloader.driver.find_element(By.TAG_NAME, "body")
            full_text = body.text

            if len(full_text) > 500:
                # Aktualizovat v databázi
                conn = sqlite3.connect(str(DB_PATH))
                cursor = conn.cursor()
                cursor.execute("UPDATE decisions SET full_text = ? WHERE id = ?", (full_text, decision_id))
                conn.commit()
                conn.close()

                job.add_result({'id': decision_id, 'text_length': len(full_text)})
                job.complete()
                logger.info(f"✅ Staženo rozhodnutí #{decision_id}: {len(full_text)} znaků")
            else:
                job.fail("Text je příliš krátký")
                logger.error(f"❌ Text rozhodnutí #{decision_id} je příliš krátký")

        except Exception as e:
            job.fail(str(e))
            logger.error(f"❌ Chyba při stahování rozhodnutí #{decision_id}: {e}")
        finally:
            downloader.close()

    thread = threading.Thread(target=background_download)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Stahování spuštěno',
        'job_id': job.job_id
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
