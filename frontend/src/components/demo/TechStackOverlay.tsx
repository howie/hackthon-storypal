/**
 * Tech stack overlay shown during the closing scene.
 * (Integrated into DemoTitleCard closing variant — this component is kept
 * as a simpler standalone if needed separately.)
 */

export function TechStackOverlay() {
  const items = [
    { category: 'AI Engine', techs: ['Gemini LLM', 'Gemini TTS', 'Gemini Imagen', 'Gemini Live API'] },
    { category: 'Backend', techs: ['FastAPI', 'SQLAlchemy', 'PostgreSQL', 'WebSocket'] },
    { category: 'Frontend', techs: ['React 18', 'TypeScript', 'Tailwind CSS', 'Zustand'] },
    { category: 'Infrastructure', techs: ['Google Cloud Run', 'Terraform', 'Docker'] },
  ]

  return (
    <div className="flex h-full flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-12 text-white">
      <h2 className="mb-8 text-3xl font-bold">Technology Stack</h2>
      <div className="grid max-w-3xl grid-cols-2 gap-6">
        {items.map((group) => (
          <div key={group.category} className="rounded-xl bg-white/10 p-5 backdrop-blur-sm">
            <h3 className="mb-3 text-lg font-semibold text-indigo-300">{group.category}</h3>
            <div className="flex flex-wrap gap-2">
              {group.techs.map((tech) => (
                <span key={tech} className="rounded-full bg-white/10 px-3 py-1 text-sm">
                  {tech}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
