export interface TextSink {
  write(text: string): void;
}

export function present(snippet: string, sink: TextSink): void {
  sink.write(snippet);
}
