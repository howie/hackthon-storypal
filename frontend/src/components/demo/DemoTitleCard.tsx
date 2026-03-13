/**
 * Animated title card for demo video intro and closing.
 */

interface DemoTitleCardProps {
  variant: 'intro' | 'closing'
}

export function DemoTitleCard({ variant }: DemoTitleCardProps) {
  if (variant === 'closing') {
    return <ClosingCard />
  }
  return <IntroCard />
}

function IntroCard() {
  return (
    <div className="flex h-full flex-col items-center justify-center bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 text-white">
      <div className="animate-fade-in-up text-center">
        <div className="mb-6 text-7xl font-extrabold tracking-tight drop-shadow-lg">
          StoryPal
        </div>
        <div className="mb-8 text-2xl font-light tracking-wide opacity-90">
          AI-Powered Interactive Story Companion
        </div>
        <div className="flex items-center justify-center gap-3 text-lg opacity-75">
          <span className="rounded-full bg-white/20 px-4 py-1.5 backdrop-blur-sm">
            Personalized Stories
          </span>
          <span className="text-white/50">&bull;</span>
          <span className="rounded-full bg-white/20 px-4 py-1.5 backdrop-blur-sm">
            Voice Interaction
          </span>
          <span className="text-white/50">&bull;</span>
          <span className="rounded-full bg-white/20 px-4 py-1.5 backdrop-blur-sm">
            AI Tutor
          </span>
        </div>
        <div className="mt-12 text-sm opacity-50">
          Built with Google Gemini
        </div>
      </div>
    </div>
  )
}

function ClosingCard() {
  return (
    <div className="flex h-full flex-col items-center justify-center bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 text-white">
      <div className="animate-fade-in-up text-center">
        <div className="mb-8 text-5xl font-extrabold tracking-tight drop-shadow-lg">
          Thank You
        </div>

        <div className="mb-10 text-xl opacity-80">
          Powered by Google Gemini Ecosystem
        </div>

        <div className="mx-auto grid max-w-2xl grid-cols-2 gap-4 text-left">
          <TechItem icon="LLM" label="Gemini Flash / Pro" desc="Story generation & reasoning" />
          <TechItem icon="TTS" label="Gemini TTS" desc="Multi-role voice synthesis" />
          <TechItem icon="IMG" label="Gemini Imagen" desc="Scene illustration generation" />
          <TechItem icon="LIVE" label="Gemini Live API" desc="Real-time voice interaction" />
        </div>

        <div className="mt-10 flex items-center justify-center gap-6 text-sm opacity-60">
          <span>FastAPI</span>
          <span>&bull;</span>
          <span>React + TypeScript</span>
          <span>&bull;</span>
          <span>PostgreSQL</span>
          <span>&bull;</span>
          <span>Google Cloud</span>
        </div>
      </div>
    </div>
  )
}

function TechItem({ icon, label, desc }: { icon: string; label: string; desc: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl bg-white/10 p-4 backdrop-blur-sm">
      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-white/20 text-xs font-bold">
        {icon}
      </div>
      <div>
        <div className="font-semibold">{label}</div>
        <div className="text-sm opacity-70">{desc}</div>
      </div>
    </div>
  )
}
