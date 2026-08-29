"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAskQuestion } from "@/hooks/use-ask-question";
import { ApiError } from "@/lib/api";
import type { AnalysisResponse } from "@/types/analysis";

function suggestedQuestions(analysis: AnalysisResponse): string[] {
  const level = analysis.fusion?.risk_level;
  if (level === "INCONCLUSIVE") {
    return [
      "Why is the result inconclusive?",
      "Which analysis layers were limited?",
      "How can I get a better source document?",
    ];
  }
  if (level === "HIGH" || level === "ELEVATED") {
    const items = ["What evidence contributed most?", "What should I manually review?"];
    if ((analysis.fusion?.corroboration.independent_layers_with_evidence.length ?? 0) >= 2) {
      items.push("Why do multiple layers agree?");
    }
    if (analysis.copy_move?.pages.some((page) => page.regions.length > 0)) {
      items.push("Which regions should I inspect?");
    }
    return items;
  }
  if (level === "MODERATE") {
    return ["Why is the risk moderate?", "What was suspicious about the metadata?", "What should I manually review?"];
  }
  return [
    "Why is this assessment low risk?",
    "What limitations apply to this analysis?",
    "Did any layer fail or complete with limited quality?",
  ];
}

export function AnalysisAssistant({ analysis }: { analysis: AnalysisResponse }) {
  const ask = useAskQuestion(analysis.analysis_id);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const suggestions = useMemo(() => suggestedQuestions(analysis), [analysis]);

  function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || ask.isPending) return;
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setInput("");
    ask.mutate(trimmed, {
      onSuccess: (result) => {
        setMessages((current) => [...current, { role: "assistant", text: result.answer }]);
      },
      onError: (error) => {
        const message = error instanceof ApiError ? error.message : "The assistant could not answer that question.";
        setMessages((current) => [...current, { role: "assistant", text: message }]);
      },
    });
  }

  return (
    <div className="flex h-full min-h-[280px] flex-col rounded-lg border bg-card">
      <div className="border-b px-4 py-3">
        <p className="text-sm font-semibold">Analysis assistant</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Answers are based only on this completed analysis. This is not a general chatbot.
        </p>
      </div>
      <div className="flex flex-wrap gap-1.5 border-b px-3 py-2">
        {suggestions.map((question) => (
          <button
            key={question}
            type="button"
            className="rounded-md border bg-background px-2 py-1 text-left text-[11px] text-muted-foreground hover:text-foreground"
            onClick={() => send(question)}
            disabled={ask.isPending || analysis.status !== "COMPLETE"}
          >
            {question}
          </button>
        ))}
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3 text-sm">
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ask about risk, evidence, limitations, or next steps for this document.</p>
        ) : (
          messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={message.role === "user" ? "text-foreground" : "text-muted-foreground"}>
              <p className="text-[11px] uppercase tracking-wide">{message.role === "user" ? "You" : "Assistant"}</p>
              <p className="mt-0.5 whitespace-pre-wrap">{message.text}</p>
            </div>
          ))
        )}
        {ask.isPending ? <p className="text-xs text-muted-foreground">Retrieving a grounded answer…</p> : null}
      </div>
      <form
        className="flex gap-2 border-t p-3"
        onSubmit={(event) => {
          event.preventDefault();
          send(input);
        }}
      >
        <input
          className="h-9 flex-1 rounded-md border bg-background px-3 text-sm"
          value={input}
          placeholder="Ask about this analysis"
          maxLength={800}
          disabled={ask.isPending || analysis.status !== "COMPLETE"}
          onChange={(event) => setInput(event.target.value)}
        />
        <Button type="submit" size="sm" disabled={!input.trim() || ask.isPending || analysis.status !== "COMPLETE"}>
          Ask
        </Button>
      </form>
    </div>
  );
}
