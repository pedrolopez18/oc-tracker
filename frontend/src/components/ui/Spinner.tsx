export function Spinner() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <div className="w-4 h-4 border-2 border-gray-200 border-t-brand rounded-full animate-spin" />
      Procesando...
    </div>
  );
}
