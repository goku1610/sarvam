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
  BrainCog
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
    customQuery = "",
    onCustomQueryChange = () => {},
    onAddCustomQuery = () => {},
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
    canEditQueries = true,
    canStartResearch = false
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
                            defaultChecked
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

                      {canEditQueries && (
                        <div className="flex flex-col gap-3 border-t border-white/8 px-4 py-4 md:flex-row">
                          <input
                            type="text"
                            value={customQuery}
                            onChange={(event) => onCustomQueryChange(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                onAddCustomQuery();
                              }
                            }}
                            placeholder="Add a custom query"
                            className="h-11 flex-1 rounded-full border border-white/10 bg-[#141517] px-4 text-sm text-stone-100 placeholder:text-stone-500 focus:outline-none"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            className="h-11 px-5 text-sm"
                            onClick={onAddCustomQuery}
                          >
                            Add query
                          </Button>
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
              {canStartResearch && !isRecording && (
                <Button
                  type="button"
                  variant="default"
                  className="h-9 px-4 text-sm"
                  onClick={() => {}}
                  disabled={isLoading}
                >
                  Start research
                </Button>
              )}

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

function App() {
  const [isLoading, setIsLoading] = React.useState(false);
  const [planSteps, setPlanSteps] = React.useState([]);
  const [queries, setQueries] = React.useState([]);
  const [customQuery, setCustomQuery] = React.useState("");
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
  const [clarifyingComplete, setClarifyingComplete] = React.useState(false);

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
      const response = await fetch("/api/clarifying-questions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
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
      const response = await fetch("/api/refine-queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
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
      }
      setClarifyingComplete(true);
    } catch (requestError) {
      setError(requestError.message || "Could not refine queries.");
      setClarifyingComplete(true);
    } finally {
      setIsRefiningQueries(false);
    }
  };

  const completeClarifyingStep = (shouldSaveAnswer) => {
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

    setIsLoading(true);
    setError("");
    setOriginalQuery(query);
    setDeepResearchActive(deepResearch);
    setPlanSteps(["Preparing plan..."]);
    setQueries([]);
    setCustomQuery("");
    resetClarificationState();
    let latestPlanSteps = ["Preparing plan..."];
    let latestQueries = [];

    try {
      const response = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
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

    if (deepResearch && latestQueries.length > 0) {
      fetchClarifyingQuestions(query, latestPlanSteps, latestQueries);
    } else {
      setClarifyingComplete(true);
    }
  };

  const addCustomQuery = () => {
    const nextQuery = customQuery.trim();
    if (!nextQuery) return;
    setQueries((current) => (current.includes(nextQuery) ? current : [...current, nextQuery]));
    setCustomQuery("");
  };

  return (
    <div className="min-h-screen px-4 py-6 md:px-8 md:py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <section className="rounded-[34px] border border-white/10 bg-[#141517]/95 p-5 shadow-[0_30px_90px_rgba(0,0,0,0.45)] backdrop-blur md:p-7">
          <div className="mb-5">
            <h1 className="m-0 text-[2rem] font-semibold text-stone-100 md:text-[2.6rem]">
              Research planner
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-stone-400 md:text-[15px]">
              Create a focused research plan, review the generated queries, and add custom ones before execution.
            </p>
          </div>

          <PromptInputBox
            onSend={handleSend}
            isLoading={isLoading}
            placeholder="Describe what you want to research"
            planSteps={planSteps}
            queries={queries}
            customQuery={customQuery}
            onCustomQueryChange={setCustomQuery}
            onAddCustomQuery={addCustomQuery}
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
            canEditQueries={!deepResearchActive || clarifyingComplete}
            canStartResearch={queries.length > 0 && (!deepResearchActive || clarifyingComplete) && !isClarifyingLoading && !isRefiningQueries}
          />

          {error ? (
            <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          ) : null}
        </section>

      </div>
    </div>
  );
}

export default App;
