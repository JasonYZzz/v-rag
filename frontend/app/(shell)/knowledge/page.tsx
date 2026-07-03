import { DocList } from "@/components/knowledge/doc-list";
import { UploadDropzone } from "@/components/knowledge/upload-dropzone";

export default function KnowledgePage() {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold">Knowledge</h1>
        <p className="mt-1 text-sm text-muted">Upload, index, and manage source documents.</p>
      </header>
      <UploadDropzone />
      <DocList />
    </div>
  );
}
