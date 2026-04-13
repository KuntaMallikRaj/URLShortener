from flask import request, jsonify, redirect, abort
from Services.URLService import URLService


class URLController:

    @staticmethod
    def shorten():
        data = request.get_json(silent=True)
        if not data or 'url' not in data:
            return jsonify({'error': 'Request body must include a "url" field'}), 400

        original_url = data['url'].strip()
        if not original_url:
            return jsonify({'error': 'URL cannot be empty'}), 400

        # Prepend scheme if missing
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url

        strategy = data.get('strategy', 'hashing')

        url = URLService.shorten_url(original_url, strategy=strategy)

        base_url = request.host_url.rstrip('/')
        return jsonify({
            'short_url': f'{base_url}/{url.short_code}',
            'short_code': url.short_code,
            'original_url': url.original_url,
            'click_count': url.click_count,
        }), 201

    @staticmethod
    def redirect_url(short_code: str):
        url = URLService.get_original_url(short_code)
        if not url:
            abort(404)
        return redirect(url.original_url, code=302)

    @staticmethod
    def get_stats(short_code: str):
        url = URLService.get_stats(short_code)
        if not url:
            return jsonify({'error': 'Short code not found'}), 404
        return jsonify(url.to_dict()), 200

    @staticmethod
    def get_recent():
        urls = URLService.get_recent_urls()
        return jsonify([u.to_dict() for u in urls]), 200
