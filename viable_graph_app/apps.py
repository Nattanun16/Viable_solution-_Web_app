from django.apps import AppConfig


class ViableGraphAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "viable_graph_app"

    def ready(self):
        """
        โหลด Sentence Transformer model ครั้งเดียวตอน Django เริ่ม
        เพื่อไม่ให้โหลดซ้ำทุก request (model มีขนาด ~400MB)
        """
        try:
            from sentence_transformers import SentenceTransformer
            import viable_graph_app.clustering as clustering_module

            clustering_module.embedding_model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2"
            )
            print("[viable_graph_app] Embedding model loaded successfully.")
        except Exception as e:
            print(f"[viable_graph_app] Warning: Could not load embedding model: {e}")
            print("[viable_graph_app] Clustering will fall back to no-grouping mode.")