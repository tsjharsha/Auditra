import { Eye, Hammer, PlayCircle } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, SectionHeader } from "../components/ui/Card";
import { Field, Input, Textarea } from "../components/ui/Field";
import { ErrorState } from "../components/ui/State";
import { SchemaRelationshipFlow } from "../features/graph/RelationshipFlow";
import { BuilderPipeline } from "../features/world/BuilderPipeline";
import { SchemaBrowser } from "../features/world/SchemaBrowser";
import { SpecEditor } from "../features/world/SpecEditor";
import { useAuditra, PROMPT_SUGGESTIONS } from "../hooks/useAuditra";

export function WorldBuilderPage() {
  const {
    prompt,
    setPrompt,
    seed,
    setSeed,
    preview,
    world,
    audit,
    error,
    isBusy,
    previewWorld,
    buildWorld,
    buildWorldFromSpec,
    auditWorld,
    runFiveMinuteDemo,
  } = useAuditra();
  const activePreview = preview ?? world;

  return (
    <div className="space-y-5">
      <Card>
        <SectionHeader title="World Builder" kicker="Prompt to specification to generated, validated financial world" />
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px]">
          <Field label="Financial Intent">
            <Textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          </Field>
          <Field label="Seed">
            <Input type="number" min={1} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </Field>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button icon={<Eye className="h-4 w-4" />} disabled={isBusy || !prompt.trim()} onClick={() => void previewWorld()}>
            Understand Prompt
          </Button>
          <Button variant="primary" icon={<Hammer className="h-4 w-4" />} disabled={isBusy || !prompt.trim()} onClick={() => void buildWorld()}>
            Build Financial World
          </Button>
          <Button icon={<PlayCircle className="h-4 w-4" />} disabled={isBusy} onClick={() => void runFiveMinuteDemo()}>
            Use Demo World
          </Button>
          <Button disabled={isBusy || !world} onClick={() => void auditWorld()}>
            Audit This World
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {PROMPT_SUGGESTIONS.map((item) => (
            <button key={item} className="rounded-lg border border-line bg-slate-50 px-3 py-2 text-left text-xs font-semibold text-steel hover:bg-white" onClick={() => setPrompt(item)}>
              {item}
            </button>
          ))}
        </div>
      </Card>

      {error ? <ErrorState title="World builder request failed" error={error} /> : null}

      <BuilderPipeline preview={preview} world={world} audit={audit} isBusy={isBusy} />
      <SpecEditor spec={activePreview?.spec} disabled={isBusy} onGenerate={(spec) => void buildWorldFromSpec(spec)} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_520px]">
        <SchemaBrowser schema={activePreview?.schema_preview} />
        <div className="min-w-0">
          <SectionHeader title="Relationship Graph" kicker="Merchant, orders, payments, settlements, refunds and fees" />
          <SchemaRelationshipFlow model={activePreview?.relationship_model} />
        </div>
      </div>
    </div>
  );
}
