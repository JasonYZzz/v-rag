export type RetrievedChunk = {
  chunk_id: string;
  text: string;
  score: number;
  page: number | null;
  document_id: string | null;
};

export type DocOut = {
  id: string;
  filename: string;
  chunks: number;
  created_at: string;
};

export type ConfigOut = {
  llm_provider: string;
  embed_provider: string;
  openai_base_url: string;
  ollama_base_url: string;
  ollama_llm_model: string;
  ollama_embed_model: string;
  embed_dim: number;
  vector_store: string;
  database_url: string;
  has_openai_key: boolean;
};

export type HealthOut = {
  status: string;
};

export type ChatStreamEvent =
  | { type: "retrieved"; chunks: RetrievedChunk[] }
  | { type: "trace"; trace_id: string }
  | { type: "token"; token: string }
  | { type: "done" };
