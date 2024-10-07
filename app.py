from flask import Flask, request, jsonify
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# .envファイルから環境変数を読み込む
load_dotenv()

app = Flask(__name__)

# ロギングの設定
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Discord webhook URL（.envファイルまたは環境変数から取得）
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
if not DISCORD_WEBHOOK_URL:
    app.logger.error('DISCORD_WEBHOOK_URL環境変数が設定されていません。')
    raise ValueError('DISCORD_WEBHOOK_URL環境変数を設定してください。')


def format_time(minutes):
    """分を時間と分に変換する関数"""
    hours, remaining_minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}時間{remaining_minutes}分"
    else:
        return f"{remaining_minutes}分"

@app.route('/receive_data', methods=['POST'])
def receive_data():
    if request.is_json:
        data = request.get_json()
        app.logger.info(f'受信したデータ: {str(data)}')
        
        if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            send_to_discord(data)
            return jsonify({"message": "データを正常に受信し、Discordに送信しました"}), 200
        else:
            app.logger.warning('受信したデータが期待される形式ではありません')
            return jsonify({"error": "データは正しい形式である必要があります"}), 400
    else:
        app.logger.warning('受信したリクエストがJSONではありません')
        return jsonify({"error": "リクエストはJSON形式である必要があります"}), 400
    

def send_to_discord(accounts_data):
    """アカウントデータをフォーマットしてDiscordに送信する関数"""
    # 日本時間で現在時刻を取得
    jst = timezone(timedelta(hours=9))
    current_time = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")
    
    # 通知の先頭に時刻を追加
    message = f":clock1: **通知時刻**: `{current_time} JST`\n"
    
    # 各アカウントのデータを追加
    for account_name, account_data in accounts_data.items():
        formatted_time = format_time(account_data.get('elapsed_time', 0))
        message += f"""
:bust_in_silhouette: **アカウント名**: `{account_name}`
:stopwatch: **経過時間**: `{formatted_time}`
:eye: **インプレッション**: `{account_data.get('impression_count', 0):,}`
:arrow_upper_right: **増加数**: `{account_data.get('increase_from_last_time', 0):,}`
:heart: **いいね数**: `{account_data.get('like_count', 0):,}`
:speech_balloon: **コメント数**: `{account_data.get('comment_count', 0):,}`
:link: **投稿URL**: {account_data.get('post_url', 'N/A')}

---
"""
    message += "==============================="
    payload = {"content": message}
    
    app.logger.info(f'{len(accounts_data)}個のアカウントデータをDiscordに送信します')
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        app.logger.info('Discordへの送信が成功しました')
    except requests.exceptions.RequestException as e:
        app.logger.error(f'Discordへの送信に失敗しました。エラー: {str(e)}')
        raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f'アプリケーションを起動します。ポート: {port}')
    app.run(host='0.0.0.0', port=port)