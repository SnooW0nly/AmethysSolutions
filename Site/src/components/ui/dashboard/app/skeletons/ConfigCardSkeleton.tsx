export function ConfigCardSkeleton() {
  return (
    <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full animate-pulse">
      {/* Header */}
      <div className="flex flex-col gap-2 mb-3">
        <div className="h-5 bg-foreground/10 rounded w-40" />
        <div className="h-3 bg-foreground/10 rounded w-full" />
        <hr className="border-foreground/5 mt-2" />
      </div>
      
      {/* Content */}
      <div className="flex flex-col gap-3">
        <div className="h-10 bg-foreground/10 rounded w-full" />
        <div className="h-10 bg-foreground/10 rounded w-full" />
        <div className="h-10 bg-foreground/10 rounded w-full" />
      </div>
      
      {/* Footer */}
      <div className="flex gap-2 mt-4">
        <div className="h-10 bg-foreground/10 rounded flex-1" />
        <div className="h-10 bg-foreground/10 rounded flex-1" />
      </div>
    </div>
  );
}
