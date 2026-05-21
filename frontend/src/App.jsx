import React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  ArrowUp,
  Paperclip,
  Square,
  X,
  StopCircle,
  Mic,
  BrainCog,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Search,
  Trash2
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

const cn = (...classes) => classes.filter(Boolean).join(" ");

const InfinityLoader = React.forwardRef(({ className, size = 24, ...props }, ref) => (
  <div
    ref={ref}
    role="status"
    aria-live="polite"
    className={cn("flex items-center justify-center", className)}
    {...props}
  >
    <svg
      viewBox="-2 -2 44 44"
      height={size}
      width={size}
      aria-hidden="true"
    >
      <path
        className="stroke-stone-500/40"
        fill="none"
        strokeWidth={4}
        pathLength={100}
        d="M29.76 18.72 c0 7.28-3.92 13.6-9.84 16.96 c-2.88 1.68-6.24 2.64-9.84 2.64 c-3.6 0-6.88-0.96-9.76-2.64 c0-7.28 3.92-13.52 9.84-16.96 c2.88-1.68 6.24-2.64 9.76-2.64 S26.88 17.04 29.76 18.72 c5.84 3.36 9.76 9.68 9.84 16.96 c-2.88 1.68-6.24 2.64-9.76 2.64 c-3.6 0-6.88-0.96-9.84-2.64 c-5.84-3.36-9.76-9.68-9.76-16.96 c0-7.28 3.92-13.6 9.76-16.96 C25.84 5.12 29.76 11.44 29.76 18.72z"
      />
      <path
        style={{ animation: "infinity-loader-travel 2s linear infinite" }}
        className="stroke-[#d6c3a1]"
        fill="none"
        strokeWidth={4}
        strokeDasharray="15, 85"
        strokeDashoffset={0}
        strokeLinecap="round"
        pathLength={100}
        d="M29.76 18.72 c0 7.28-3.92 13.6-9.84 16.96 c-2.88 1.68-6.24 2.64-9.84 2.64 c-3.6 0-6.88-0.96-9.76-2.64 c0-7.28 3.92-13.52 9.84-16.96 c2.88-1.68 6.24-2.64 9.76-2.64 S26.88 17.04 29.76 18.72 c5.84 3.36 9.76 9.68 9.84 16.96 c-2.88 1.68-6.24 2.64-9.76 2.64 c-3.6 0-6.88-0.96-9.84-2.64 c-5.84-3.36-9.76-9.68-9.76-16.96 c0-7.28 3.92-13.6 9.76-16.96 C25.84 5.12 29.76 11.44 29.76 18.72z"
      />
    </svg>
    <span className="sr-only">Loading...</span>
  </div>
));
InfinityLoader.displayName = "InfinityLoader";

const StepIndicator = ({ label, className }) => (
  <div
    className={cn(
      "flex items-center gap-3 rounded-2xl border border-[#d6c3a1]/15 bg-[#d6c3a1]/[0.035] px-4 py-3",
      className
    )}
  >
    <InfinityLoader size={25} />
    <span className="step-wave-text text-sm font-medium">{label}</span>
  </div>
);

const renderInlineMarkdown = (text) => {
  const parts = [];
  const tokenPattern = /(\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\*\*([^*]+)\*\*|(https?:\/\/[^\s)]+))/g;
  let lastIndex = 0;
  let match;

  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] && match[3]) {
      parts.push(
        <a
          key={`link-${match.index}`}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[#ecdcc0] underline decoration-[#d6c3a1]/35 underline-offset-4 transition-colors hover:text-white"
        >
          {match[2]}
        </a>
      );
    } else if (match[4]) {
      parts.push(
        <strong key={`bold-${match.index}`} className="font-semibold text-stone-50">
          {match[4]}
        </strong>
      );
    } else if (match[5]) {
      const trailingPunctuation = match[5].match(/[.,;:!?]+$/)?.[0] || "";
      const url = trailingPunctuation ? match[5].slice(0, -trailingPunctuation.length) : match[5];
      parts.push(
        <a
          key={`bare-link-${match.index}`}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[#ecdcc0] underline decoration-[#d6c3a1]/35 underline-offset-4 transition-colors hover:text-white"
        >
          {url}
        </a>
      );
      if (trailingPunctuation) parts.push(trailingPunctuation);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
};

const MarkdownAnswer = ({ text }) => {
  if (!text) return null;

  return (
    <div className="space-y-4 text-[15px] leading-8 text-stone-100">
      {text.split(/\n+/).map((rawLine, index) => {
        const line = rawLine.trim();
        if (!line) return null;

        const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
        if (headingMatch) {
          const level = headingMatch[1].length;
          const headingClasses = level <= 2
            ? "pt-2 text-xl font-semibold text-stone-50"
            : "pt-1 text-base font-semibold text-stone-50";
          return (
            <h3 key={`${line}-${index}`} className={cn("m-0", headingClasses)}>
              {renderInlineMarkdown(headingMatch[2])}
            </h3>
          );
        }

        const orderedMatch = line.match(/^(\d+)\.\s+(.+)$/);
        if (orderedMatch) {
          return (
            <div key={`${line}-${index}`} className="flex gap-3">
              <span className="min-w-5 text-right text-stone-500">{orderedMatch[1]}.</span>
              <p className="m-0 flex-1">{renderInlineMarkdown(orderedMatch[2])}</p>
            </div>
          );
        }

        const bulletMatch = line.match(/^[-*]\s+(.+)$/);
        if (bulletMatch) {
          return (
            <div key={`${line}-${index}`} className="flex gap-3">
              <span className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-stone-500" />
              <p className="m-0 flex-1">{renderInlineMarkdown(bulletMatch[1])}</p>
            </div>
          );
        }

        return (
          <p key={`${line}-${index}`} className="m-0">
            {renderInlineMarkdown(line)}
          </p>
        );
      })}
    </div>
  );
};

const Textarea = React.forwardRef(({ className, ...props }, ref) => (
  <textarea
    className={cn(
      "flex min-h-[44px] w-full resize-none border-none bg-transparent px-3 py-2.5 text-base text-stone-100 placeholder:text-stone-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    ref={ref}
    rows={1}
    {...props}
  />
));
Textarea.displayName = "Textarea";

const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;
const TooltipContent = React.forwardRef(({ className, sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-xl border border-white/10 bg-[#1c1d20] px-3 py-1.5 text-sm text-stone-100 shadow-xl",
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

const Dialog = DialogPrimitive.Root;
const DialogPortal = DialogPrimitive.Portal;
const DialogOverlay = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn("fixed inset-0 z-50 bg-black/70 backdrop-blur-sm", className)}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-1/2 top-1/2 z-50 w-full max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-[28px] bg-transparent p-0 shadow-none",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 z-10 rounded-full bg-[#2a2b2f]/90 p-2 transition hover:bg-[#33353a]">
        <X className="h-5 w-5 text-stone-100" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogTitle = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight text-stone-100", className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const Button = React.forwardRef(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const variantClasses = {
      default: "bg-stone-100 text-stone-950 hover:bg-white",
      outline: "border border-white/12 bg-transparent text-stone-100 hover:bg-white/[0.06]",
      ghost: "bg-transparent text-stone-300 hover:bg-white/[0.06] hover:text-stone-100"
    };
    const sizeClasses = {
      default: "h-10 px-4 py-2",
      sm: "h-8 px-3 text-sm",
      lg: "h-12 px-6",
      icon: "h-9 w-9 rounded-full"
    };

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-full font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

const VoiceRecorder = ({
  isRecording,
  onStartRecording,
  onStopRecording,
  visualizerBars = 28
}) => {
  const [time, setTime] = React.useState(0);
  const timerRef = React.useRef(null);

  React.useEffect(() => {
    if (isRecording) {
      onStartRecording();
      timerRef.current = setInterval(() => setTime((t) => t + 1), 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (time > 0) {
        onStopRecording(time);
      }
      setTime(0);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className={cn(
        "flex w-full flex-col items-center justify-center py-3 transition-all duration-300",
        isRecording ? "opacity-100" : "h-0 opacity-0"
      )}
    >
      <div className="mb-3 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
        <span className="font-mono text-sm text-stone-300">{formatTime(time)}</span>
      </div>
      <div className="flex h-10 w-full items-center justify-center gap-1 px-4">
        {[...Array(visualizerBars)].map((_, index) => (
          <div
            key={index}
            className="w-0.5 rounded-full bg-stone-100/60 animate-pulse"
            style={{
              height: `${Math.max(15, Math.random() * 100)}%`,
              animationDelay: `${index * 0.05}s`,
              animationDuration: `${0.5 + Math.random() * 0.5}s`
            }}
          />
        ))}
      </div>
    </div>
  );
};

const ImageViewDialog = ({ imageUrl, onClose }) => {
  if (!imageUrl) return null;

  return (
    <Dialog open={Boolean(imageUrl)} onOpenChange={onClose}>
      <DialogContent className="max-w-[90vw] md:max-w-[880px]">
        <DialogTitle className="sr-only">Image Preview</DialogTitle>
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="overflow-hidden rounded-[28px] border border-white/10 bg-[#17181b] shadow-2xl"
        >
          <img
            src={imageUrl}
            alt="Full preview"
            className="max-h-[80vh] w-full object-contain"
          />
        </motion.div>
      </DialogContent>
    </Dialog>
  );
};

const DeleteChatDialog = ({ session, onCancel, onConfirm }) => {
  if (!session) return null;

  return (
    <Dialog open={Boolean(session)} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="max-w-[92vw] md:max-w-[420px]">
        <DialogTitle className="sr-only">Delete Chat</DialogTitle>
        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.97, y: 8 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="overflow-hidden rounded-[26px] border border-white/10 bg-[#17181b] p-5 shadow-2xl"
        >
          <h2 className="m-0 text-lg font-semibold text-stone-100">Delete chat?</h2>
          <p className="mt-2 text-sm leading-6 text-stone-400">
            This will permanently remove “{session.title || "Untitled research"}” from your saved research history.
          </p>
          <div className="mt-5 flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              className="h-10 px-4 text-sm"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="default"
              className="h-10 bg-red-200 px-4 text-sm text-red-950 hover:bg-red-100"
              onClick={() => onConfirm(session)}
            >
              Delete
            </Button>
          </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
};

const SearchResultsPanel = ({
  isOpen,
  isSearching,
  results,
  error,
  status,
  onClose
}) => (
  <AnimatePresence>
    {isOpen && (
      <motion.aside
        layout
        initial={{ opacity: 0, x: 28 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 28 }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        className="fixed bottom-4 right-4 top-4 z-40 flex w-[min(420px,calc(100vw-32px))] flex-col overflow-hidden rounded-[28px] border border-white/10 bg-[#141517]/98 shadow-[0_24px_80px_rgba(0,0,0,0.5)] backdrop-blur lg:sticky lg:top-8 lg:z-10 lg:h-[calc(100vh-4rem)] lg:min-w-[360px] lg:max-w-[420px] lg:shrink-0"
      >
        <div className="flex items-center justify-between border-b border-white/8 px-5 py-4">
          <div>
            <h2 className="m-0 text-base font-semibold text-stone-100">Sources</h2>
            <p className="m-0 mt-1 text-xs text-stone-500">{results.length} links collected</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full text-stone-400 transition-colors hover:bg-white/[0.06] hover:text-stone-100"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close sources</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isSearching && (
            <StepIndicator label={status || "Searching and reading sources"} className="mb-3" />
          )}

          {error && (
            <div className="mb-3 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          {results.length === 0 && !isSearching && !error && (
            <div className="rounded-2xl border border-white/8 bg-white/[0.025] px-4 py-5 text-sm text-stone-400">
              No sources yet.
            </div>
          )}

          <div className="space-y-3">
            {results.map((result, index) => (
              <motion.a
                key={`${result.url}-${index}`}
                href={result.url}
                target="_blank"
                rel="noreferrer"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
                className="block rounded-2xl border border-white/8 bg-white/[0.025] px-4 py-3 transition-colors hover:border-[#d6c3a1]/25 hover:bg-[#d6c3a1]/[0.035]"
              >
                <div className="line-clamp-2 text-sm font-medium leading-6 text-stone-100">
                  {result.title || result.domain || result.url}
                </div>
                <div className="mt-1 truncate text-xs text-stone-500">{result.domain}</div>
              </motion.a>
            ))}
          </div>
        </div>
      </motion.aside>
    )}
  </AnimatePresence>
);

const HistorySidebar = ({
  isOpen,
  sessions,
  activeSessionId,
  searchValue,
  onSearchChange,
  onToggle,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession
}) => {
  const [openMenuId, setOpenMenuId] = React.useState("");
  const [renamingId, setRenamingId] = React.useState("");
  const [renameValue, setRenameValue] = React.useState("");

  React.useEffect(() => {
    const closeMenu = () => setOpenMenuId("");
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  return (
    <motion.aside
    layout
    initial={false}
    animate={{ width: isOpen ? 280 : 58 }}
    transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
    className="sticky top-6 z-30 hidden h-[calc(100vh-3rem)] shrink-0 overflow-hidden rounded-[28px] border border-white/10 bg-[#111214]/98 shadow-[0_24px_70px_rgba(0,0,0,0.42)] backdrop-blur lg:flex lg:flex-col"
  >
    <div className="flex h-full min-w-[58px]">
      <div className="flex w-[58px] shrink-0 flex-col items-center border-r border-white/8 px-2 py-3">
        <button
          type="button"
          onClick={onToggle}
          title={isOpen ? "Collapse history" : "Expand history"}
          className="flex h-10 w-10 items-center justify-center rounded-full text-stone-300 transition-colors hover:bg-white/[0.06] hover:text-stone-100"
        >
          {isOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
          <span className="sr-only">{isOpen ? "Collapse history" : "Expand history"}</span>
        </button>

        <button
          type="button"
          onClick={onNewChat}
          title="New research"
          className="mt-3 flex h-10 w-10 items-center justify-center rounded-full border border-[#d6c3a1]/20 bg-[#d6c3a1]/[0.06] text-[#ecdcc0] transition-colors hover:border-[#d6c3a1]/35 hover:bg-[#d6c3a1]/[0.1]"
        >
          <Plus className="h-5 w-5" />
          <span className="sr-only">New research</span>
        </button>
      </div>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="history-content"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="flex min-w-[222px] flex-1 flex-col"
          >
            <div className="border-b border-white/8 p-4">
              <div className="mb-3">
                <h2 className="m-0 text-base font-semibold text-stone-100">Research history</h2>
                <p className="m-0 mt-1 text-xs text-stone-500">{sessions.length} saved chats</p>
              </div>

              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
                <input
                  type="search"
                  value={searchValue}
                  onChange={(event) => onSearchChange(event.target.value)}
                  placeholder="Search previous chats"
                  className="h-11 w-full rounded-full border border-white/10 bg-[#17181b] pl-9 pr-4 text-sm text-stone-100 placeholder:text-stone-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">
                Previous chats
              </div>

              {sessions.length === 0 ? (
                <div className="rounded-2xl border border-white/8 bg-white/[0.025] px-4 py-5 text-sm leading-6 text-stone-500">
                  No matching research chats yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {sessions.map((session) => {
                    const isActive = activeSessionId === session.session_id;
                    const isRenaming = renamingId === session.session_id;
                    return (
                      <div
                        key={session.session_id}
                        className="group relative"
                      >
                        <div
                          className={cn(
                            "w-full rounded-2xl border px-3 py-3 pr-10 text-left transition-colors",
                            isActive
                              ? "border-[#d6c3a1]/30 bg-[#d6c3a1]/[0.08]"
                              : "border-white/8 bg-white/[0.025] hover:border-white/14 hover:bg-white/[0.05]"
                          )}
                        >
                          {isRenaming ? (
                            <input
                              autoFocus
                              type="text"
                              value={renameValue}
                              onChange={(event) => setRenameValue(event.target.value)}
                              onClick={(event) => event.stopPropagation()}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  event.preventDefault();
                                  const nextTitle = renameValue.trim();
                                  if (nextTitle) onRenameSession(session, nextTitle);
                                  setRenamingId("");
                                  setRenameValue("");
                                }
                                if (event.key === "Escape") {
                                  setRenamingId("");
                                  setRenameValue("");
                                }
                              }}
                              onBlur={() => {
                                const nextTitle = renameValue.trim();
                                if (nextTitle && nextTitle !== session.title) {
                                  onRenameSession(session, nextTitle);
                                }
                                setRenamingId("");
                                setRenameValue("");
                              }}
                              className="h-8 w-full rounded-xl border border-[#d6c3a1]/30 bg-[#111214] px-3 text-sm font-medium text-stone-100 focus:outline-none"
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => onSelectSession(session.session_id)}
                              className="block w-full text-left"
                            >
                              <div className="line-clamp-2 text-sm font-medium leading-5 text-stone-100">
                                {session.title || "Untitled research"}
                              </div>
                              {session.original_query && session.original_query !== session.title ? (
                                <div className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">
                                  {session.original_query}
                                </div>
                              ) : null}
                            </button>
                          )}
                        </div>

                        {!isRenaming && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setOpenMenuId((current) => current === session.session_id ? "" : session.session_id);
                            }}
                            className={cn(
                              "absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full text-stone-400 opacity-0 transition hover:bg-white/[0.08] hover:text-stone-100 group-hover:opacity-100",
                              openMenuId === session.session_id && "opacity-100"
                            )}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                            <span className="sr-only">Chat options</span>
                          </button>
                        )}

                        <AnimatePresence>
                          {openMenuId === session.session_id && (
                            <motion.div
                              initial={{ opacity: 0, y: -4, scale: 0.98 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: -4, scale: 0.98 }}
                              transition={{ duration: 0.14, ease: "easeOut" }}
                              onClick={(event) => event.stopPropagation()}
                              className="absolute right-2 top-10 z-20 w-36 overflow-hidden rounded-2xl border border-white/10 bg-[#191a1d] p-1 shadow-[0_18px_50px_rgba(0,0,0,0.45)]"
                            >
                              <button
                                type="button"
                                onClick={() => {
                                  setOpenMenuId("");
                                  setRenamingId(session.session_id);
                                  setRenameValue(session.title || "Untitled research");
                                }}
                                className="flex h-9 w-full items-center gap-2 rounded-xl px-3 text-left text-sm text-stone-200 transition hover:bg-white/[0.06]"
                              >
                                <Pencil className="h-4 w-4" />
                                Rename
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setOpenMenuId("");
                                  onDeleteSession(session);
                                }}
                                className="flex h-9 w-full items-center gap-2 rounded-xl px-3 text-left text-sm text-red-200 transition hover:bg-red-500/10"
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete
                              </button>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  </motion.aside>
  );
};

const PromptInputContext = React.createContext({
  isLoading: false,
  value: "",
  setValue: () => {},
  maxHeight: 240,
  onSubmit: undefined,
  disabled: false
});

function usePromptInput() {
  return React.useContext(PromptInputContext);
}

const PromptInput = React.forwardRef(
  (
    {
      className,
      isLoading = false,
      maxHeight = 240,
      value,
      onValueChange,
      onSubmit,
      children,
      disabled = false,
      onDragOver,
      onDragLeave,
      onDrop
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = React.useState(value || "");
    const handleChange = (newValue) => {
      setInternalValue(newValue);
      onValueChange?.(newValue);
    };

    return (
      <TooltipProvider>
        <PromptInputContext.Provider
          value={{
            isLoading,
            value: value ?? internalValue,
            setValue: onValueChange ?? handleChange,
            maxHeight,
            onSubmit,
            disabled
          }}
        >
          <div
            ref={ref}
            className={cn(
              "rounded-[30px] border border-white/10 bg-[#17181b] p-2 shadow-[0_18px_60px_rgba(0,0,0,0.35)] transition-all duration-300",
              isLoading && "border-stone-400/30",
              className
            )}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          >
            {children}
          </div>
        </PromptInputContext.Provider>
      </TooltipProvider>
    );
  }
);
PromptInput.displayName = "PromptInput";

const PromptInputTextarea = ({
  className,
  onKeyDown,
  disableAutosize = false,
  placeholder,
  ...props
}) => {
  const { value, setValue, maxHeight, onSubmit, disabled } = usePromptInput();
  const textareaRef = React.useRef(null);

  React.useEffect(() => {
    if (disableAutosize || !textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, maxHeight)}px`;
  }, [value, maxHeight, disableAutosize]);

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit?.();
    }
    onKeyDown?.(event);
  };

  return (
    <Textarea
      ref={textareaRef}
      value={value}
      onChange={(event) => setValue(event.target.value)}
      onKeyDown={handleKeyDown}
      className={cn("text-[15px] leading-7", className)}
      disabled={disabled}
      placeholder={placeholder}
      {...props}
    />
  );
};

const PromptInputActions = ({ children, className, ...props }) => (
  <div className={cn("flex items-center gap-2", className)} {...props}>
    {children}
  </div>
);

const PromptInputAction = ({
  tooltip,
  children,
  className,
  side = "top",
  ...props
}) => {
  const { disabled } = usePromptInput();

  return (
    <Tooltip {...props}>
      <TooltipTrigger asChild disabled={disabled}>
        {children}
      </TooltipTrigger>
      <TooltipContent side={side} className={className}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
};

const PromptInputBox = React.forwardRef(
  ({
    onSend = () => {},
    isLoading = false,
    placeholder = "Type your message here...",
    className,
    planSteps = [],
    queries = [],
    planRevisionRequest = "",
    onPlanRevisionRequestChange = () => {},
    onRevisePlan = () => {},
    clarifyingQuestions = [],
    activeClarifyingIndex = 0,
    selectedClarifyingAnswer = "",
    customClarifyingAnswer = "",
    onSelectClarifyingAnswer = () => {},
    onCustomClarifyingAnswerChange = () => {},
    onSubmitClarifyingAnswer = () => {},
    onSkipClarifyingQuestion = () => {},
    isClarifyingLoading = false,
    isRefiningQueries = false,
    isRevisingPlan = false,
    canEditQueries = true,
    canRevisePlan = true,
    canStartResearch = false,
    selectedQueries = [],
    onToggleQuery = () => {},
    onStartResearch = () => {},
    isSearching = false
  }, ref) => {
    const [input, setInput] = React.useState("");
    const [files, setFiles] = React.useState([]);
    const [filePreviews, setFilePreviews] = React.useState({});
    const [selectedImage, setSelectedImage] = React.useState(null);
    const [isRecording, setIsRecording] = React.useState(false);
    const [deepResearch, setDeepResearch] = React.useState(false);
    const uploadInputRef = React.useRef(null);
    const hasPlan = planSteps.length > 0;
    const hasQueries = queries.length > 0;
    const hasSubmittedQuery = hasPlan || hasQueries || isLoading;
    const activeClarifyingQuestion = clarifyingQuestions[activeClarifyingIndex];
    const hasClarifyingQuestion = Boolean(activeClarifyingQuestion);

    const isImageFile = (file) => file.type.startsWith("image/");

    const processFile = (file) => {
      if (!isImageFile(file)) return;
      if (file.size > 10 * 1024 * 1024) return;
      setFiles([file]);
      const reader = new FileReader();
      reader.onload = (event) => setFilePreviews({ [file.name]: event.target?.result });
      reader.readAsDataURL(file);
    };

    const handleDragOver = React.useCallback((event) => {
      event.preventDefault();
      event.stopPropagation();
    }, []);

    const handleDragLeave = React.useCallback((event) => {
      event.preventDefault();
      event.stopPropagation();
    }, []);

    const handleDrop = React.useCallback((event) => {
      event.preventDefault();
      event.stopPropagation();
      const droppedFiles = Array.from(event.dataTransfer.files);
      const imageFiles = droppedFiles.filter((file) => isImageFile(file));
      if (imageFiles.length > 0) processFile(imageFiles[0]);
    }, []);

    const handleRemoveFile = (index) => {
      const fileToRemove = files[index];
      if (fileToRemove && filePreviews[fileToRemove.name]) setFilePreviews({});
      setFiles([]);
    };

    const handlePaste = React.useCallback((event) => {
      const items = event.clipboardData?.items;
      if (!items) return;
      for (let index = 0; index < items.length; index += 1) {
        if (items[index].type.includes("image")) {
          const file = items[index].getAsFile();
          if (file) {
            event.preventDefault();
            processFile(file);
            break;
          }
        }
      }
    }, []);

    React.useEffect(() => {
      document.addEventListener("paste", handlePaste);
      return () => document.removeEventListener("paste", handlePaste);
    }, [handlePaste]);

    const handleSubmit = () => {
      if (!(input.trim() || files.length > 0)) return;
      onSend(input, files, { deepResearch });
      setInput("");
      setFiles([]);
      setFilePreviews({});
    };

    const handleStartRecording = () => {};

    const handleStopRecording = (duration) => {
      setIsRecording(false);
      onSend(`[Voice message - ${duration} seconds]`, []);
    };

    const hasContent = input.trim() !== "" || files.length > 0;

    return (
      <>
        <PromptInput
          value={input}
          onValueChange={setInput}
          isLoading={isLoading}
          onSubmit={handleSubmit}
          className={cn("w-full bg-[#17181b] border-white/10", className)}
          disabled={isLoading || isRecording}
          ref={ref}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {files.length > 0 && !isRecording && (
            <div className="flex flex-wrap gap-2 px-1 pb-1">
              {files.map((file, index) => (
                <div key={file.name + index} className="relative group">
                  {file.type.startsWith("image/") && filePreviews[file.name] && (
                    <div
                      className="h-16 w-16 cursor-pointer overflow-hidden rounded-2xl border border-white/10"
                      onClick={() => setSelectedImage(filePreviews[file.name])}
                    >
                      <img
                        src={filePreviews[file.name]}
                        alt={file.name}
                        className="h-full w-full object-cover"
                      />
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          handleRemoveFile(index);
                        }}
                        className="absolute right-1 top-1 rounded-full bg-black/70 p-1"
                      >
                        <X className="h-3 w-3 text-white" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className={cn("transition-all duration-300", isRecording ? "h-0 overflow-hidden opacity-0" : "opacity-100")}>
            <PromptInputTextarea
              placeholder={deepResearch ? "Ask for a deep research plan..." : placeholder}
              disabled={hasSubmittedQuery}
            />
          </div>

          <AnimatePresence>
            {(hasPlan || hasQueries) && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.24, ease: "easeOut" }}
                className="overflow-hidden"
              >
                <div className="mt-3 overflow-hidden rounded-[24px] border border-white/8 bg-[#1b1c1f]">
                  {hasPlan && (
                    <div>
                      <div className="border-b border-white/8 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">
                        Plan
                      </div>
                      {planSteps
                        .filter((step) => step !== "Preparing plan...")
                        .map((step, index) => (
                          <div
                            key={step + index}
                            className="flex items-start gap-4 border-b border-white/6 px-4 py-4 last:border-b-0"
                          >
                            <span className="mt-1.5 h-5 w-5 rounded-full border-[1.5px] border-dashed border-white/25" />
                            <p className="m-0 text-[15px] leading-7 text-stone-100">
                              {step}
                            </p>
                          </div>
                        ))}
                      {isLoading && (
                        <div className="border-t border-white/8 px-4 py-4">
                          <StepIndicator label="Generating plan and queries" />
                        </div>
                      )}
                    </div>
                  )}

                  {hasQueries && (
                    <div className={cn(hasPlan && "border-t border-white/8")}>
                      <div className="border-b border-white/8 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">
                        Queries
                      </div>
                      {queries.map((query, index) => (
                        <label
                          key={query + index}
                          className="flex cursor-pointer items-start gap-4 border-b border-white/6 px-4 py-3 last:border-b-0"
                        >
                          <input
                            type="checkbox"
                            checked={selectedQueries.includes(query)}
                            onChange={() => onToggleQuery(query)}
                            className="mt-1 h-5 w-5 rounded-full border border-white/20 bg-transparent accent-stone-100"
                          />
                          <span className="text-[14px] leading-6 text-stone-200">{query}</span>
                        </label>
                      ))}

                      {isClarifyingLoading && (
                        <div className="border-t border-white/8 px-4 py-4">
                          <StepIndicator label="Preparing narrowing questions" />
                        </div>
                      )}

                      {hasClarifyingQuestion && !canEditQueries && !isRefiningQueries && (
                        <div className="border-t border-white/8 px-4 py-4">
                          <StepIndicator
                            label={`Question ${activeClarifyingIndex + 1} of ${clarifyingQuestions.length}`}
                            className="mb-4"
                          />
                          <p className="m-0 mb-4 border-l border-[#d6c3a1]/30 pl-4 text-[15px] leading-7 text-stone-100">
                            {activeClarifyingQuestion.question}
                          </p>
                          <div className="mb-3 flex flex-wrap gap-2">
                            {activeClarifyingQuestion.options.map((option) => (
                              <button
                                key={option}
                                type="button"
                                onClick={() => onSelectClarifyingAnswer(option)}
                                className={cn(
                                  "rounded-full border px-3 py-2 text-sm transition-colors",
                                  selectedClarifyingAnswer === option
                                    ? "border-[#d6c3a1]/45 bg-[#d6c3a1]/10 text-[#ecdcc0]"
                                    : "border-white/10 text-stone-300 hover:bg-white/[0.06]"
                                )}
                              >
                                {option}
                              </button>
                            ))}
                          </div>
                          <input
                            type="text"
                            value={customClarifyingAnswer}
                            onChange={(event) => onCustomClarifyingAnswerChange(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                onSubmitClarifyingAnswer();
                              }
                            }}
                            placeholder="Custom answer"
                            className="mb-3 h-11 w-full rounded-full border border-white/10 bg-[#141517] px-4 text-sm text-stone-100 placeholder:text-stone-500 focus:outline-none"
                          />
                          <div className="flex justify-end gap-2">
                            <Button
                              type="button"
                              variant="ghost"
                              className="h-10 px-4 text-sm"
                              onClick={onSkipClarifyingQuestion}
                              disabled={isRefiningQueries}
                            >
                              Skip
                            </Button>
                            <Button
                              type="button"
                              variant="default"
                              className="h-10 px-4 text-sm"
                              onClick={onSubmitClarifyingAnswer}
                              disabled={isRefiningQueries}
                            >
                              {activeClarifyingIndex + 1 === clarifyingQuestions.length ? "Refine queries" : "Next"}
                            </Button>
                          </div>
                        </div>
                      )}

                      {isRefiningQueries && (
                        <div className="border-t border-white/8 px-4 py-4">
                          <StepIndicator label="Refining queries" />
                        </div>
                      )}

                      {canRevisePlan && (
                        <div className="border-t border-white/8 px-4 py-4">
                          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">
                            Revise plan
                          </div>
                          <div className="flex flex-col gap-3 md:flex-row">
                            <input
                              type="text"
                              value={planRevisionRequest}
                              onChange={(event) => onPlanRevisionRequestChange(event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  event.preventDefault();
                                  onRevisePlan();
                                }
                              }}
                              placeholder="Ask to adjust scope, sources, region, timeframe..."
                              className="h-11 flex-1 rounded-full border border-white/10 bg-[#141517] px-4 text-sm text-stone-100 placeholder:text-stone-500 focus:outline-none"
                              disabled={isRevisingPlan || !canEditQueries}
                            />
                            <Button
                              type="button"
                              variant="outline"
                              className="h-11 px-5 text-sm"
                              onClick={onRevisePlan}
                              disabled={isRevisingPlan || !planRevisionRequest.trim() || !canEditQueries}
                            >
                              {isRevisingPlan ? "Revising" : "Revise plan"}
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {isRecording && (
            <VoiceRecorder
              isRecording={isRecording}
              onStartRecording={handleStartRecording}
              onStopRecording={handleStopRecording}
            />
          )}

          <PromptInputActions className="justify-between gap-2 px-1 pt-2">
            <div className={cn("flex items-center gap-2 transition-opacity duration-300", isRecording ? "invisible h-0 opacity-0" : "visible opacity-100")}>
              {!hasSubmittedQuery && (
                <>
                  <PromptInputAction tooltip="Upload image">
                    <button
                      onClick={() => uploadInputRef.current?.click()}
                      className="flex h-8 w-8 items-center justify-center rounded-full text-stone-400 transition-colors hover:bg-white/[0.06] hover:text-stone-200"
                      disabled={isRecording}
                    >
                      <Paperclip className="h-[18px] w-[18px]" />
                      <input
                        ref={uploadInputRef}
                        type="file"
                        className="hidden"
                        onChange={(event) => {
                          if (event.target.files && event.target.files.length > 0) processFile(event.target.files[0]);
                          if (event.target) event.target.value = "";
                        }}
                        accept="image/*"
                      />
                    </button>
                  </PromptInputAction>

                  <button
                    type="button"
                    onClick={() => setDeepResearch((prev) => !prev)}
                    aria-pressed={deepResearch}
                    title="Deep research"
                    className={cn(
                      "flex h-8 items-center gap-1 rounded-full border px-2.5 transition-all",
                      deepResearch
                        ? "border-[#d6c3a1]/45 bg-[#d6c3a1]/10 text-[#ecdcc0]"
                        : "border-transparent bg-transparent text-stone-400 hover:text-stone-200"
                    )}
                  >
                    <div className="flex h-5 w-5 items-center justify-center">
                      <motion.div
                        animate={{ rotate: deepResearch ? 360 : 0, scale: deepResearch ? 1.08 : 1 }}
                        whileHover={{ rotate: deepResearch ? 360 : 12, scale: 1.08 }}
                        transition={{ type: "spring", stiffness: 260, damping: 24 }}
                      >
                        <BrainCog className={cn("h-4 w-4", deepResearch ? "text-[#ecdcc0]" : "text-inherit")} />
                      </motion.div>
                    </div>
                    <AnimatePresence>
                      {deepResearch && (
                        <motion.span
                          initial={{ width: 0, opacity: 0 }}
                          animate={{ width: "auto", opacity: 1 }}
                          exit={{ width: 0, opacity: 0 }}
                          transition={{ duration: 0.18 }}
                          className="overflow-hidden whitespace-nowrap text-xs font-medium tracking-wide"
                        >
                          Deep research
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </button>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              <AnimatePresence>
                {canStartResearch && !isRecording && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.96, x: 6 }}
                    animate={{ opacity: 1, scale: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.96, x: 6 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                  >
                    <Button
                      type="button"
                      variant="default"
                      className="h-9 px-4 text-sm"
                      onClick={onStartResearch}
                      disabled={isLoading || isSearching || selectedQueries.length === 0}
                    >
                      Start research
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>

              {!hasQueries && (
                <PromptInputAction
                  tooltip={
                    isLoading
                      ? "Generating"
                      : isRecording
                        ? "Stop recording"
                        : hasContent
                          ? "Generate plan"
                          : "Voice message"
                  }
                >
                  <Button
                    variant="default"
                    size="icon"
                    className={cn(
                      "transition-all duration-200",
                      isRecording
                        ? "bg-transparent text-red-500 hover:bg-white/[0.06] hover:text-red-400"
                        : hasContent
                          ? "bg-stone-100 text-stone-950 hover:bg-white"
                          : "bg-transparent text-stone-400 hover:bg-white/[0.06] hover:text-stone-200"
                    )}
                    onClick={() => {
                      if (isRecording) setIsRecording(false);
                      else if (hasContent) handleSubmit();
                      else setIsRecording(true);
                    }}
                    disabled={isLoading && !hasContent}
                  >
                    {isLoading ? (
                      <Square className="h-4 w-4 fill-stone-950 animate-pulse" />
                    ) : isRecording ? (
                      <StopCircle className="h-5 w-5" />
                    ) : hasContent ? (
                      <ArrowUp className="h-4 w-4" />
                    ) : (
                      <Mic className="h-[18px] w-[18px]" />
                    )}
                  </Button>
                </PromptInputAction>
              )}
            </div>
          </PromptInputActions>
        </PromptInput>

        <ImageViewDialog imageUrl={selectedImage} onClose={() => setSelectedImage(null)} />
      </>
    );
  }
);
PromptInputBox.displayName = "PromptInputBox";

function splitPlanIntoSteps(planText) {
  return planText
    .split(/\n+/)
    .flatMap((line) => line.split(/(?<=[.?!])\s+/))
    .map((line) => line.trim())
    .filter(Boolean);
}

const MAX_DEEP_RESEARCH_ITERATIONS = 3;

function App() {
  const [sessionId, setSessionId] = React.useState("");
  const [sessionHistory, setSessionHistory] = React.useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = React.useState(false);
  const [historySearch, setHistorySearch] = React.useState("");
  const [chatTitle, setChatTitle] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [planSteps, setPlanSteps] = React.useState([]);
  const [queries, setQueries] = React.useState([]);
  const [planRevisionRequest, setPlanRevisionRequest] = React.useState("");
  const [error, setError] = React.useState("");
  const [originalQuery, setOriginalQuery] = React.useState("");
  const [deepResearchActive, setDeepResearchActive] = React.useState(false);
  const [clarifyingQuestions, setClarifyingQuestions] = React.useState([]);
  const [activeClarifyingIndex, setActiveClarifyingIndex] = React.useState(0);
  const [clarifyingAnswers, setClarifyingAnswers] = React.useState([]);
  const [selectedClarifyingAnswer, setSelectedClarifyingAnswer] = React.useState("");
  const [customClarifyingAnswer, setCustomClarifyingAnswer] = React.useState("");
  const [isClarifyingLoading, setIsClarifyingLoading] = React.useState(false);
  const [isRefiningQueries, setIsRefiningQueries] = React.useState(false);
  const [isRevisingPlan, setIsRevisingPlan] = React.useState(false);
  const [clarifyingComplete, setClarifyingComplete] = React.useState(false);
  const [selectedQueries, setSelectedQueries] = React.useState([]);
  const [isSearchPanelOpen, setIsSearchPanelOpen] = React.useState(false);
  const [isSearching, setIsSearching] = React.useState(false);
  const [searchStatus, setSearchStatus] = React.useState("");
  const [searchResults, setSearchResults] = React.useState([]);
  const [researchContext, setResearchContext] = React.useState(null);
  const [finalAnswer, setFinalAnswer] = React.useState("");
  const [answerStatus, setAnswerStatus] = React.useState("");
  const [searchError, setSearchError] = React.useState("");
  const [sessionPendingDelete, setSessionPendingDelete] = React.useState(null);
  const sessionIdRef = React.useRef("");

  const resetWorkspaceState = () => {
    setChatTitle("");
    setIsLoading(false);
    setPlanSteps([]);
    setQueries([]);
    setPlanRevisionRequest("");
    setError("");
    setOriginalQuery("");
    setDeepResearchActive(false);
    setClarifyingQuestions([]);
    setActiveClarifyingIndex(0);
    setClarifyingAnswers([]);
    setSelectedClarifyingAnswer("");
    setCustomClarifyingAnswer("");
    setIsClarifyingLoading(false);
    setIsRefiningQueries(false);
    setIsRevisingPlan(false);
    setClarifyingComplete(false);
    setSelectedQueries([]);
    setIsSearchPanelOpen(false);
    setIsSearching(false);
    setSearchStatus("");
    setSearchResults([]);
    setResearchContext(null);
    setFinalAnswer("");
    setAnswerStatus("");
    setSearchError("");
  };

  const hydrateFromSession = (session) => {
    resetWorkspaceState();
    const savedState = session?.state || {};
    setChatTitle(savedState.chat_title || "");
    if (savedState.original_query) setOriginalQuery(savedState.original_query);
    if (typeof savedState.deep_research_active === "boolean") {
      setDeepResearchActive(savedState.deep_research_active);
    }
    if (Array.isArray(savedState.plan_steps)) setPlanSteps(savedState.plan_steps);
    if (Array.isArray(savedState.queries)) setQueries(savedState.queries);
    if (Array.isArray(savedState.selected_queries)) setSelectedQueries(savedState.selected_queries);
    if (Array.isArray(savedState.clarifying_questions)) {
      setClarifyingQuestions(savedState.clarifying_questions);
    }
    if (Number.isInteger(savedState.active_clarifying_index)) {
      setActiveClarifyingIndex(savedState.active_clarifying_index);
    }
    if (Array.isArray(savedState.clarifying_answers)) {
      setClarifyingAnswers(savedState.clarifying_answers);
    }
    if (typeof savedState.clarifying_complete === "boolean") {
      setClarifyingComplete(savedState.clarifying_complete);
    }
    if (Array.isArray(savedState.search_results)) setSearchResults(savedState.search_results);
    if (savedState.research_context) setResearchContext(savedState.research_context);
    if (typeof savedState.final_answer === "string") setFinalAnswer(savedState.final_answer);
    if (typeof savedState.search_error === "string") setSearchError(savedState.search_error);
    if (typeof savedState.is_search_panel_open === "boolean") {
      setIsSearchPanelOpen(savedState.is_search_panel_open);
    }
  };

  const ensureSession = async () => {
    if (sessionIdRef.current) return sessionIdRef.current;

    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });

    if (!response.ok) {
      throw new Error("Could not initialize local session.");
    }

    const session = await response.json();
    sessionIdRef.current = session.session_id;
    setSessionId(session.session_id);
    return session.session_id;
  };

  const fetchSessionHistory = async () => {
    try {
      const response = await fetch("/api/sessions");
      if (!response.ok) throw new Error("Could not load history.");
      const data = await response.json();
      setSessionHistory(Array.isArray(data.sessions) ? data.sessions : []);
    } catch (historyError) {
      console.warn("Could not load session history.", historyError);
    }
  };

  const startNewChat = () => {
    sessionIdRef.current = "";
    setSessionId("");
    resetWorkspaceState();
  };

  const loadSession = async (nextSessionId) => {
    try {
      const response = await fetch(`/api/sessions/${nextSessionId}`);
      if (!response.ok) throw new Error("Could not load saved research chat.");
      const session = await response.json();
      sessionIdRef.current = session.session_id;
      setSessionId(session.session_id);
      hydrateFromSession(session);
    } catch (sessionError) {
      setError(sessionError.message || "Could not load saved research chat.");
    }
  };

  const renameSession = async (session, nextTitleValue) => {
    const currentTitle = session.title || "Untitled research";
    const nextTitle = nextTitleValue?.trim();
    if (!nextTitle || nextTitle === currentTitle) return;

    try {
      const response = await fetch(`/api/sessions/${session.session_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: {
            chat_title: nextTitle,
            history_sort_at: session.sort_at || session.updated_at || session.created_at
          },
          event: { type: "chat_renamed", title: nextTitle }
        })
      });
      if (!response.ok) throw new Error("Could not rename chat.");
      if (session.session_id === sessionIdRef.current) {
        setChatTitle(nextTitle);
      }
      fetchSessionHistory();
    } catch (renameError) {
      setError(renameError.message || "Could not rename chat.");
    }
  };

  const requestDeleteSession = (session) => {
    setSessionPendingDelete(session);
  };

  const confirmDeleteSession = async (session) => {
    try {
      const response = await fetch(`/api/sessions/${session.session_id}`, {
        method: "DELETE"
      });
      if (!response.ok) throw new Error("Could not delete chat.");
      if (session.session_id === sessionIdRef.current) {
        sessionIdRef.current = "";
        setSessionId("");
        resetWorkspaceState();
      }
      fetchSessionHistory();
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete chat.");
    } finally {
      setSessionPendingDelete(null);
    }
  };

  const saveSessionState = async (state, event) => {
    try {
      const activeSessionId = await ensureSession();
      const response = await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state, event })
      });
      if (response.ok) {
        fetchSessionHistory();
      }
    } catch (sessionError) {
      console.warn("Could not save local session.", sessionError);
    }
  };

  React.useEffect(() => {
    fetchSessionHistory();
  }, []);

  const resetClarificationState = () => {
    setClarifyingQuestions([]);
    setActiveClarifyingIndex(0);
    setClarifyingAnswers([]);
    setSelectedClarifyingAnswer("");
    setCustomClarifyingAnswer("");
    setIsClarifyingLoading(false);
    setIsRefiningQueries(false);
    setClarifyingComplete(false);
  };

  const fetchClarifyingQuestions = async (query, plan, searchQueries) => {
    setIsClarifyingLoading(true);
    try {
      const activeSessionId = await ensureSession();
      const response = await fetch("/api/clarifying-questions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query,
          plan,
          search_queries: searchQueries
        })
      });

      if (!response.ok) {
        throw new Error("Could not generate narrowing questions.");
      }

      const data = await response.json();
      const questions = Array.isArray(data.questions) ? data.questions : [];
      setClarifyingQuestions(questions);
      setClarifyingComplete(questions.length === 0);
      saveSessionState(
        {
          clarifying_questions: questions,
          clarifying_complete: questions.length === 0
        },
        { type: "clarifying_questions_hydrated", count: questions.length }
      );
    } catch (requestError) {
      setError(requestError.message || "Could not generate narrowing questions.");
      setClarifyingComplete(true);
    } finally {
      setIsClarifyingLoading(false);
    }
  };

  const refineQueries = async (answers) => {
    if (answers.length === 0) {
      setClarifyingComplete(true);
      return;
    }

    setIsRefiningQueries(true);
    try {
      const activeSessionId = await ensureSession();
      const response = await fetch("/api/refine-queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query: originalQuery,
          plan: planSteps,
          search_queries: queries,
          answers
        })
      });

      if (!response.ok) {
        throw new Error("Could not refine queries.");
      }

      const data = await response.json();
      if (Array.isArray(data.search_queries) && data.search_queries.length > 0) {
        setQueries(data.search_queries);
        setSelectedQueries(data.search_queries);
        saveSessionState(
          {
            queries: data.search_queries,
            selected_queries: data.search_queries,
            clarifying_complete: true
          },
          { type: "queries_refined_in_ui", count: data.search_queries.length }
        );
      }
      setClarifyingComplete(true);
    } catch (requestError) {
      setError(requestError.message || "Could not refine queries.");
      setClarifyingComplete(true);
    } finally {
      setIsRefiningQueries(false);
    }
  };

  const completeClarifyingStep = async (shouldSaveAnswer) => {
    const currentQuestion = clarifyingQuestions[activeClarifyingIndex];
    if (!currentQuestion) return;

    const answer = customClarifyingAnswer.trim() || selectedClarifyingAnswer.trim();
    const nextAnswers = shouldSaveAnswer && answer
      ? [...clarifyingAnswers, { question: currentQuestion.question, answer }]
      : clarifyingAnswers;
    const isLastQuestion = activeClarifyingIndex + 1 >= clarifyingQuestions.length;

    setClarifyingAnswers(nextAnswers);
    setSelectedClarifyingAnswer("");
    setCustomClarifyingAnswer("");
    await saveSessionState(
      {
        clarifying_answers: nextAnswers,
        active_clarifying_index: isLastQuestion ? activeClarifyingIndex : activeClarifyingIndex + 1
      },
      { type: shouldSaveAnswer ? "clarifying_answer_saved" : "clarifying_question_skipped" }
    );

    if (isLastQuestion) {
      refineQueries(nextAnswers);
    } else {
      setActiveClarifyingIndex((currentIndex) => currentIndex + 1);
    }
  };

  const handleSend = async (message, _files, options = {}) => {
    const query = message.trim();
    if (!query) return;
    const deepResearch = Boolean(options.deepResearch);
    const activeSessionId = await ensureSession();

    setIsLoading(true);
    setError("");
    setOriginalQuery(query);
    setDeepResearchActive(deepResearch);
    setPlanSteps(["Preparing plan..."]);
    setQueries([]);
    setSelectedQueries([]);
    setPlanRevisionRequest("");
    setSearchResults([]);
    setResearchContext(null);
    setFinalAnswer("");
    setAnswerStatus("");
    setSearchError("");
    setSearchStatus("");
    setIsSearchPanelOpen(false);
    resetClarificationState();
    await saveSessionState(
      {
        chat_title: "",
        original_query: query,
        deep_research_active: deepResearch,
        plan_steps: ["Preparing plan..."],
        queries: [],
        selected_queries: [],
        clarifying_questions: [],
        clarifying_answers: [],
        clarifying_complete: false,
        search_results: [],
        research_context: null,
        final_answer: "",
        search_error: "",
        is_search_panel_open: false
      },
      { type: "new_query_started", query, deep_research: deepResearch }
    );
    let latestChatTitle = query.slice(0, 48);
    let latestPlanSteps = ["Preparing plan..."];
    let latestQueries = [];

    try {
      const response = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query,
          deep_research: deepResearch
        })
      });

      if (!response.ok || !response.body) {
        throw new Error("Planner request failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let rawData = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        rawData += decoder.decode(value, { stream: true });

        if (rawData.includes("<TITLE_END>")) {
          const match = rawData.match(/<TITLE_START>([\s\S]*?)<TITLE_END>/);
          const titleContent = match?.[1]?.trim();
          if (titleContent) {
            latestChatTitle = titleContent;
            setChatTitle(latestChatTitle);
          }
        }

        if (rawData.includes("<PLAN_START>")) {
          const parts = rawData.split("<PLAN_START>");
          if (parts.length > 1) {
            const planContent = parts[1].split("<PLAN_END>")[0].trim();
            latestPlanSteps = splitPlanIntoSteps(planContent);
            setPlanSteps(latestPlanSteps);
          }
        }

        if (rawData.includes("<QUERIES_END>")) {
          const match = rawData.match(/<QUERIES_START>([\s\S]*?)<QUERIES_END>/);
          if (match) {
            try {
              const parsedQueries = JSON.parse(match[1].trim());
              latestQueries = parsedQueries;
              setQueries(latestQueries);
              setSelectedQueries(latestQueries);
            } catch (parseError) {
              console.error("Failed to parse queries.", parseError);
            }
          }
        }
      }
    } catch (requestError) {
      setError(requestError.message || "Something went wrong while generating the plan.");
    } finally {
      setIsLoading(false);
    }

    await saveSessionState(
      {
        chat_title: latestChatTitle,
        original_query: query,
        deep_research_active: deepResearch,
        plan_steps: latestPlanSteps,
        queries: latestQueries,
        selected_queries: latestQueries
      },
      { type: "plan_completed", query_count: latestQueries.length }
    );

    if (deepResearch && latestQueries.length > 0) {
      fetchClarifyingQuestions(query, latestPlanSteps, latestQueries);
    } else {
      setClarifyingComplete(true);
    }
  };

  const revisePlan = async () => {
    const revisionRequest = planRevisionRequest.trim();
    if (!revisionRequest || isRevisingPlan || hasResearchStarted) return;

    setIsRevisingPlan(true);
    setError("");
    try {
      const activeSessionId = await ensureSession();
      const response = await fetch("/api/revise-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query: originalQuery,
          plan: planSteps,
          search_queries: queries,
          revision_request: revisionRequest,
          deep_research: deepResearchActive
        })
      });

      if (!response.ok) {
        throw new Error("Could not revise the plan.");
      }

      const data = await response.json();
      const revisedPlan = Array.isArray(data.plan_steps) ? data.plan_steps : planSteps;
      const revisedQueries = Array.isArray(data.search_queries) ? data.search_queries : queries;

      setPlanSteps(revisedPlan);
      setQueries(revisedQueries);
      setSelectedQueries(revisedQueries);
      setPlanRevisionRequest("");
      resetClarificationState();
      await saveSessionState(
        {
          plan_steps: revisedPlan,
          queries: revisedQueries,
          selected_queries: revisedQueries,
          clarifying_questions: [],
          clarifying_answers: [],
          clarifying_complete: !deepResearchActive
        },
        { type: "plan_revision_applied", revision_request: revisionRequest }
      );

      if (deepResearchActive && revisedQueries.length > 0) {
        fetchClarifyingQuestions(originalQuery, revisedPlan, revisedQueries);
      } else {
        setClarifyingComplete(true);
      }
    } catch (requestError) {
      setError(requestError.message || "Could not revise the plan.");
    } finally {
      setIsRevisingPlan(false);
    }
  };

  const toggleQuerySelection = (query) => {
    setSelectedQueries((current) => {
      const nextSelectedQueries = current.includes(query)
        ? current.filter((selectedQuery) => selectedQuery !== query)
        : [...current, query];
      saveSessionState(
        { selected_queries: nextSelectedQueries },
        { type: "query_selection_changed", count: nextSelectedQueries.length }
      );
      return nextSelectedQueries;
    });
  };

  const startResearch = async () => {
    if (
      selectedQueries.length === 0 ||
      isSearching ||
      searchResults.length > 0 ||
      Boolean(researchContext) ||
      Boolean(finalAnswer) ||
      Boolean(searchError)
    ) {
      return;
    }

    const activeSessionId = await ensureSession();

    setIsSearchPanelOpen(true);
    setIsSearching(true);
    setSearchResults([]);
    setResearchContext(null);
    setFinalAnswer("");
    setAnswerStatus("");
    setSearchError("");
    setSearchStatus("Searching and reading sources");

    const seenUrls = new Set();
    const collectedSources = [];
    const contextChunks = [];
    let latestResearchContext = null;
    let searchedQueries = [...selectedQueries];

    const handleSearchEvent = (event) => {
      if (event.type === "result") {
        if (event.url && seenUrls.has(event.url)) return;
        if (event.url) seenUrls.add(event.url);
        collectedSources.push(event);
        setSearchResults((current) => [...current, event]);
      }
      if (event.type === "error") {
        setSearchError(event.message || "Search failed.");
      }
      if (event.type === "progress") {
        setSearchStatus(event.message || "Searching and reading sources");
      }
      if (event.type === "context_ready") {
        const nextContext = {
          chunks: Array.isArray(event.chunks) ? event.chunks : [],
          context: event.context || "",
          chunkCount: event.chunk_count || 0,
          selectedCount: event.selected_count || 0
        };
        contextChunks.push(...nextContext.chunks);
        latestResearchContext = {
          ...nextContext,
          chunks: [...contextChunks],
          selectedCount: contextChunks.length
        };
        setResearchContext(latestResearchContext);
      }
    };

    const runSearchBatch = async (queriesToSearch, iterationLabel) => {
      setSearchStatus(iterationLabel || "Searching and reading sources");

      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query: originalQuery,
          queries: queriesToSearch
        })
      });

      if (!response.ok || !response.body) {
        throw new Error("Search request failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        lines.forEach((line) => {
          if (!line.trim()) return;
          const event = JSON.parse(line);
          handleSearchEvent(event);
        });
      }

      if (buffer.trim()) {
        const event = JSON.parse(buffer);
        handleSearchEvent(event);
      }
    };

    try {
      await runSearchBatch(selectedQueries, "Searching and reading sources");
      await saveSessionState(
        {
          selected_queries: selectedQueries,
          search_results: collectedSources,
          research_context: latestResearchContext,
          search_error: "",
          is_search_panel_open: true
        },
        { type: "initial_search_completed", result_count: collectedSources.length }
      );

      if (deepResearchActive) {
        for (let iteration = 1; iteration <= MAX_DEEP_RESEARCH_ITERATIONS; iteration += 1) {
          setSearchStatus("Checking whether more searches are needed");

          const response = await fetch("/api/follow-up-queries", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: activeSessionId,
              query: originalQuery,
              plan: planSteps,
              searched_queries: searchedQueries,
              sources: contextChunks.length > 0
                ? contextChunks.map((chunk) => ({
                    title: chunk.title,
                    url: chunk.url,
                    domain: chunk.domain,
                    content: chunk.text
                  }))
                : collectedSources,
              iteration
            })
          });

          if (!response.ok) {
            throw new Error("Could not check for follow-up searches.");
          }

          const data = await response.json();
          const previousQueries = new Set(
            searchedQueries.map((searchedQuery) => searchedQuery.trim().toLowerCase())
          );
          const followUpQueries = Array.isArray(data.search_queries)
            ? data.search_queries
                .map((query) => String(query).trim())
                .filter((query) => query && !previousQueries.has(query.toLowerCase()))
            : [];

          if (followUpQueries.length === 0) break;

          searchedQueries = [...searchedQueries, ...followUpQueries];
          setQueries((current) => {
            const currentQuerySet = new Set(current.map((query) => query.toLowerCase()));
            const newQueries = followUpQueries.filter((query) => !currentQuerySet.has(query.toLowerCase()));
            const nextQueries = [...current, ...newQueries];
            saveSessionState(
              { queries: nextQueries, selected_queries: [...searchedQueries] },
              { type: "follow_up_queries_added", iteration, count: followUpQueries.length }
            );
            return nextQueries;
          });
          setSelectedQueries((current) => {
            const currentQuerySet = new Set(current.map((query) => query.toLowerCase()));
            const newQueries = followUpQueries.filter((query) => !currentQuerySet.has(query.toLowerCase()));
            return [...current, ...newQueries];
          });

          await runSearchBatch(
            followUpQueries,
            `Deep research follow-up ${iteration}: searching ${followUpQueries.length} new ${followUpQueries.length === 1 ? "query" : "queries"}`
          );
          await saveSessionState(
            { search_results: collectedSources, research_context: latestResearchContext, is_search_panel_open: true },
            { type: "follow_up_search_completed", iteration, result_count: collectedSources.length }
          );
        }
      }

      if (latestResearchContext?.context) {
        setAnswerStatus("Generating answer with citations");
        const answerResponse = await fetch("/api/answer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: activeSessionId,
            query: originalQuery,
            plan: planSteps,
            search_queries: searchedQueries,
            context: latestResearchContext.context,
            chunks: latestResearchContext.chunks
          })
        });

        if (!answerResponse.ok || !answerResponse.body) {
          throw new Error("Answer generation failed.");
        }

        const answerReader = answerResponse.body.getReader();
        const answerDecoder = new TextDecoder("utf-8");
        let answerBuffer = "";
        let nextAnswer = "";

        while (true) {
          const { done, value } = await answerReader.read();
          if (done) break;

          answerBuffer += answerDecoder.decode(value, { stream: true });
          const lines = answerBuffer.split("\n");
          answerBuffer = lines.pop() || "";

          lines.forEach((line) => {
            if (!line.trim()) return;
            const event = JSON.parse(line);
            if (event.type === "progress") {
              setAnswerStatus(event.message || "Generating answer with citations");
            }
            if (event.type === "token") {
              nextAnswer += event.text || "";
              setFinalAnswer(nextAnswer);
            }
            if (event.type === "done") {
              nextAnswer = event.answer || nextAnswer;
              setFinalAnswer(nextAnswer);
            }
            if (event.type === "error") {
              setSearchError(event.message || "Answer generation failed.");
            }
          });
        }

        if (answerBuffer.trim()) {
          const event = JSON.parse(answerBuffer);
          if (event.type === "done") {
            nextAnswer = event.answer || nextAnswer;
            setFinalAnswer(nextAnswer);
          }
        }

        await saveSessionState(
          { final_answer: nextAnswer, search_results: collectedSources, research_context: latestResearchContext },
          { type: "answer_rendered", answer_length: nextAnswer.length }
        );
      }
    } catch (requestError) {
      setSearchError(requestError.message || "Search failed.");
      await saveSessionState(
        {
          search_error: requestError.message || "Search failed.",
          search_results: collectedSources,
          research_context: latestResearchContext
        },
        { type: "search_failed" }
      );
    } finally {
      setIsSearching(false);
      setSearchStatus("");
      setAnswerStatus("");
      await saveSessionState(
        { search_results: collectedSources, research_context: latestResearchContext, is_search_panel_open: true },
        { type: "search_finished", result_count: collectedSources.length }
      );
    }
  };

  const canReopenSearchPanel = !isSearchPanelOpen && (searchResults.length > 0 || isSearching || Boolean(searchError));
  const hasResearchStarted = Boolean(
    isSearching ||
      searchResults.length > 0 ||
      researchContext ||
      finalAnswer ||
      searchError
  );
  const hasWorkspaceContent = Boolean(
    originalQuery ||
      chatTitle ||
      isLoading ||
      error ||
      planSteps.length > 0 ||
      queries.length > 0 ||
      clarifyingQuestions.length > 0 ||
      isClarifyingLoading ||
      isRefiningQueries ||
      isRevisingPlan ||
      isSearching ||
      searchResults.length > 0 ||
      finalAnswer ||
      searchError
  );
  const visibleSessionHistory = sessionHistory.filter((session) => {
    const searchTerm = historySearch.trim().toLowerCase();
    if (!searchTerm) return true;
    return `${session.title || ""} ${session.original_query || ""}`.toLowerCase().includes(searchTerm);
  });

  return (
    <div className="min-h-screen px-4 py-6 md:px-8 lg:py-6">
      <motion.div
        layout
        transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
        className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-[1640px] items-start gap-5"
      >
        <HistorySidebar
          isOpen={isHistoryOpen}
          sessions={visibleSessionHistory}
          activeSessionId={sessionId}
          searchValue={historySearch}
          onSearchChange={setHistorySearch}
          onToggle={() => setIsHistoryOpen((current) => !current)}
          onNewChat={startNewChat}
          onSelectSession={loadSession}
          onRenameSession={renameSession}
          onDeleteSession={requestDeleteSession}
        />

        <motion.main
          layout
          transition={{ duration: 0.46, ease: [0.22, 1, 0.36, 1] }}
          className={cn(
            "flex min-h-[calc(100vh-3rem)] min-w-0 flex-1 justify-center",
            hasWorkspaceContent ? "items-start" : "items-center"
          )}
        >
          <motion.section
            layout
            animate={{
              y: hasWorkspaceContent ? 0 : -8,
              maxWidth: hasWorkspaceContent ? 1120 : 880
            }}
            transition={{ duration: 0.46, ease: [0.22, 1, 0.36, 1] }}
            className="w-full rounded-[34px] border border-white/10 bg-[#141517]/95 p-5 shadow-[0_30px_90px_rgba(0,0,0,0.45)] backdrop-blur md:p-7"
          >
            <div className="mb-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <h1 className="m-0 text-[2rem] font-semibold text-stone-100 md:text-[2.6rem]">
                    {chatTitle || "Research planner"}
                  </h1>
                  <p className="mt-2 max-w-2xl text-sm leading-7 text-stone-400 md:text-[15px]">
                    {originalQuery
                      ? originalQuery
                      : "Create a focused research plan, review the generated queries, and add custom ones before execution."}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={startNewChat}
                  className="inline-flex h-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] px-4 text-sm font-medium text-stone-300 transition-colors hover:bg-white/[0.06] hover:text-stone-100 lg:hidden"
                >
                  New research
                </button>

                <AnimatePresence>
                  {canReopenSearchPanel && (
                    <motion.button
                      type="button"
                      onClick={async () => {
                        setIsSearchPanelOpen(true);
                        await saveSessionState(
                          { is_search_panel_open: true },
                          { type: "sources_panel_reopened" }
                        );
                      }}
                      initial={{ opacity: 0, y: -8, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.96 }}
                      transition={{ duration: 0.22, ease: "easeOut" }}
                      className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-full border border-[#d6c3a1]/20 bg-[#d6c3a1]/[0.06] px-4 text-sm font-medium text-[#ecdcc0] shadow-[0_12px_30px_rgba(0,0,0,0.18)] transition-colors hover:border-[#d6c3a1]/35 hover:bg-[#d6c3a1]/[0.1]"
                    >
                      Sources
                      <span className="rounded-full bg-[#d6c3a1]/15 px-2 py-0.5 text-xs text-[#f5e7cf]">
                        {searchResults.length}
                      </span>
                    </motion.button>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <PromptInputBox
              onSend={handleSend}
              isLoading={isLoading}
              placeholder="Describe what you want to research"
              planSteps={planSteps}
              queries={queries}
              planRevisionRequest={planRevisionRequest}
              onPlanRevisionRequestChange={setPlanRevisionRequest}
              onRevisePlan={revisePlan}
              clarifyingQuestions={clarifyingQuestions}
              activeClarifyingIndex={activeClarifyingIndex}
              selectedClarifyingAnswer={selectedClarifyingAnswer}
              customClarifyingAnswer={customClarifyingAnswer}
              onSelectClarifyingAnswer={setSelectedClarifyingAnswer}
              onCustomClarifyingAnswerChange={setCustomClarifyingAnswer}
              onSubmitClarifyingAnswer={() => completeClarifyingStep(true)}
              onSkipClarifyingQuestion={() => completeClarifyingStep(false)}
              isClarifyingLoading={isClarifyingLoading}
              isRefiningQueries={isRefiningQueries}
              isRevisingPlan={isRevisingPlan}
              canEditQueries={!deepResearchActive || clarifyingComplete}
              canRevisePlan={queries.length > 0 && !hasResearchStarted}
              canStartResearch={queries.length > 0 && !hasResearchStarted && (!deepResearchActive || clarifyingComplete) && !isClarifyingLoading && !isRefiningQueries && !isRevisingPlan}
              selectedQueries={selectedQueries}
              onToggleQuery={toggleQuerySelection}
              onStartResearch={startResearch}
              isSearching={isSearching}
            />

            <AnimatePresence>
              {(answerStatus || finalAnswer) && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 12 }}
                  transition={{ duration: 0.24, ease: "easeOut" }}
                  className="mt-5 overflow-hidden rounded-[28px] border border-white/10 bg-[#17181b] shadow-[0_18px_60px_rgba(0,0,0,0.28)]"
                >
                  <div className="border-b border-white/8 px-5 py-4">
                    <h2 className="m-0 text-base font-semibold text-stone-100">Answer</h2>
                    {answerStatus ? (
                      <p className="m-0 mt-1 text-xs text-stone-500">{answerStatus}</p>
                    ) : null}
                  </div>
                  <div className="px-5 py-5">
                    {finalAnswer ? (
                      <MarkdownAnswer text={finalAnswer} />
                    ) : (
                      <StepIndicator label={answerStatus || "Generating answer with citations"} />
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {error ? (
              <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            ) : null}
          </motion.section>
        </motion.main>

        <SearchResultsPanel
          isOpen={isSearchPanelOpen}
          isSearching={isSearching}
          results={searchResults}
          error={searchError}
          status={searchStatus}
          onClose={() => {
            setIsSearchPanelOpen(false);
            saveSessionState(
              { is_search_panel_open: false },
              { type: "sources_panel_closed" }
            );
          }}
        />

        <DeleteChatDialog
          session={sessionPendingDelete}
          onCancel={() => setSessionPendingDelete(null)}
          onConfirm={confirmDeleteSession}
        />
      </motion.div>
    </div>
  );
}

export default App;
