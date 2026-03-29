interface Props { comments: string | null }

export function CommentTimeline({ comments }: Props) {
  if (!comments) return <p className="text-xs text-gray-400 italic">Sin comentarios</p>;

  const entries = comments
    .split(/\n{2,}/)
    .filter(Boolean)
    .map((entry, i) => ({ id: i, text: entry.trim() }));

  return (
    <div className="space-y-3">
      {entries.map(e => (
        <div key={e.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-2 h-2 rounded-full bg-gray-300 mt-1.5 flex-shrink-0" />
            {e.id < entries.length - 1 && <div className="w-px flex-1 bg-gray-100 mt-1" />}
          </div>
          <p className="text-sm text-gray-600 leading-relaxed pb-3">{e.text}</p>
        </div>
      ))}
    </div>
  );
}
