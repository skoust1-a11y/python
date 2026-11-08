import type { QueryResponse } from "@/api/types";

import type { ResponseMode } from "@/lib/responseModes";

import { Card } from "./Card";

import { ConfidenceScore } from "./ConfidenceScore";

import { ResponseModeToggles } from "./ResponseModeToggles";

import { MarkdownAnswer } from "@/components/chat/MarkdownAnswer";
import { SourcesList } from "./SourcesList";



interface QueryResultPanelProps {

  response: QueryResponse;

  activeMode: ResponseMode;

  onModeChange: (mode: ResponseMode) => void;

}



export function QueryResultPanel({ response, activeMode, onModeChange }: QueryResultPanelProps) {

  return (

    <div className="space-y-4">

      <Card title="Response mode">

        <div className="space-y-3">

          <ResponseModeToggles activeMode={activeMode} onModeChange={onModeChange} />

          <MarkdownAnswer text={response[activeMode]} />

        </div>

      </Card>



      <div className="grid gap-4 md:grid-cols-2">

        <Card title="Confidence">

          <ConfidenceScore

            score={response.confidence}

            level={response.confidence_level}

            verificationNotice={response.verification_notice}

            size="lg"

          />

          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">

            Shared across all response modes from a single retrieval.

          </p>

        </Card>

        <Card title={`Sources (${response.sources.length})`}>

          <SourcesList sources={response.sources} />

        </Card>

      </div>



      {response.related_documents.length > 0 && (

        <Card title={`Related Documents (${response.related_documents.length})`}>

          <ul className="space-y-2">

            {response.related_documents.map((doc) => (

              <li

                key={doc.document_id ?? doc.name}

                className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800"

              >

                <span className="font-medium text-slate-800 dark:text-slate-200">{doc.name}</span>

                <span className="text-xs text-slate-500">

                  Relevance: {(doc.relevance * 100).toFixed(0)}%

                </span>

              </li>

            ))}

          </ul>

        </Card>

      )}



      {response.follow_up_questions.length > 0 && (

        <Card title="Follow-up Questions">

          <ul className="list-inside list-disc space-y-1 text-sm text-slate-700 dark:text-slate-300">

            {response.follow_up_questions.map((question) => (

              <li key={question}>{question}</li>

            ))}

          </ul>

        </Card>

      )}

    </div>

  );

}

