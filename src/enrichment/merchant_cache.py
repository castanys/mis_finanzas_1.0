"""
Caché SQLite para resultados de Google Places API.
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict


class MerchantCache:
    """Caché persistente para evitar consultas repetidas a Google Places API."""

    def __init__(self, db_path: str = 'merchant_cache.db'):
        """
        Inicializa el caché SQLite.

        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        """Crea la tabla si no existe."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchant_cache (
                merchant_name TEXT NOT NULL,
                search_location TEXT NOT NULL,
                google_place_id TEXT,
                google_place_name TEXT,
                google_place_type TEXT,
                google_place_types TEXT,
                mapped_cat2 TEXT,
                confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (merchant_name, search_location)
            )
        ''')
        self.conn.commit()

    def get(self, merchant_name: str, search_location: str = 'cartagena') -> Optional[Dict]:
        """
        Busca un merchant en el caché.

        Args:
            merchant_name: Nombre del merchant
            search_location: Ámbito de búsqueda ('cartagena', 'spain', 'europe', 'global')

        Returns:
            Dict con los datos del caché o None si no existe
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM merchant_cache
            WHERE merchant_name = ? AND search_location = ?
        ''', (merchant_name, search_location))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_any_location(self, merchant_name: str) -> Optional[Dict]:
        """
        Busca un merchant en cualquier ámbito geográfico.
        Útil para saber si ya se buscó en algún scope.

        Args:
            merchant_name: Nombre del merchant

        Returns:
            Dict con los datos del caché o None si no existe en ningún scope
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM merchant_cache
            WHERE merchant_name = ?
            ORDER BY
                CASE search_location
                    WHEN 'cartagena' THEN 1
                    WHEN 'spain' THEN 2
                    WHEN 'europe' THEN 3
                    WHEN 'global' THEN 4
                END
            LIMIT 1
        ''', (merchant_name,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def save(self, merchant_name: str, search_location: str, result: Dict):
        """
        Guarda un resultado en el caché.

        Args:
            merchant_name: Nombre del merchant
            search_location: Ámbito de búsqueda
            result: Diccionario con los datos de Google Places
                - google_place_id: ID del lugar (None si no hay resultado)
                - google_place_name: Nombre del lugar
                - google_place_type: Tipo principal
                - google_place_types: Todos los tipos separados por |
                - mapped_cat2: Cat2 mapeado
                - confidence: 'high', 'medium', 'low', 'no_result'
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO merchant_cache
            (merchant_name, search_location, google_place_id, google_place_name,
             google_place_type, google_place_types, mapped_cat2, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            merchant_name,
            search_location,
            result.get('google_place_id'),
            result.get('google_place_name'),
            result.get('google_place_type'),
            result.get('google_place_types'),
            result.get('mapped_cat2'),
            result.get('confidence'),
            datetime.now()
        ))
        self.conn.commit()

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del caché.

        Returns:
            Dict con estadísticas
        """
        cursor = self.conn.cursor()

        # Total entries
        cursor.execute('SELECT COUNT(*) FROM merchant_cache')
        total = cursor.fetchone()[0]

        # By confidence
        cursor.execute('''
            SELECT confidence, COUNT(*) as count
            FROM merchant_cache
            GROUP BY confidence
        ''')
        by_confidence = {row['confidence']: row['count'] for row in cursor.fetchall()}

        # By location
        cursor.execute('''
            SELECT search_location, COUNT(*) as count
            FROM merchant_cache
            GROUP BY search_location
        ''')
        by_location = {row['search_location']: row['count'] for row in cursor.fetchall()}

        # With results (no_result = false)
        cursor.execute('''
            SELECT COUNT(*) FROM merchant_cache
            WHERE confidence != 'no_result'
        ''')
        with_results = cursor.fetchone()[0]

        return {
            'total': total,
            'with_results': with_results,
            'no_results': total - with_results,
            'by_confidence': by_confidence,
            'by_location': by_location,
        }

    def close(self):
        """Cierra la conexión a la base de datos."""
        self.conn.close()
