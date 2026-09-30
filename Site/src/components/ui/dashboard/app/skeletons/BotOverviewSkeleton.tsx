export function BotOverviewSkeleton() {
  return (
    <div className="flex flex-col bg-foreground/2 border border-foreground/5 rounded-xl p-5 w-full animate-pulse">
      <div className="flex flex-col lg:flex-row lg:justify-between items-center w-full">
        <div className="flex flex-col w-full gap-2">
          {/* Nome e ID */}
          <div className="h-7 bg-foreground/10 rounded w-48" />
          <div className="h-4 bg-foreground/10 rounded w-64" />
        </div>
        
        <div className="flex flex-col lg:flex-row lg:flex-wrap gap-2 lg:gap-2 mt-3 lg:mt-0 w-full lg:justify-end">
          {/* Cards de expiração e RAM */}
          <div className="bg-foreground/5 border border-foreground/2 rounded-lg p-2 h-16 w-full lg:flex-1 lg:min-w-[240px] lg:max-w-[300px]" />
          <div className="bg-foreground/5 border border-foreground/2 rounded-lg p-2 h-16 w-full lg:flex-1 lg:min-w-[240px] lg:max-w-[300px]" />
        </div>
      </div>
      
      <hr className="my-2 border-foreground/4" />
      
      <div className="flex flex-row items-center w-full gap-2">
        {/* Status badge */}
        <div className="h-7 bg-foreground/10 rounded-full w-32" />
        <div className="flex-1" />
        <div className="h-4 bg-foreground/10 rounded w-40" />
      </div>
    </div>
  );
}
