export const MobileActions = ({
    open,
    onToggle,
}: {
    open: boolean;
    onToggle: () => void;
}) => {
    return (
        <div className="items-center box-border caret-transparent gap-x-2 flex shrink-0 min-h-[auto] min-w-[auto] outline-[3px] gap-y-2 no-underline md:hidden">
            {/* <button
                type="button"
                title="Switch site language to Russian"
                className="bg-transparent caret-transparent text-white/50 block text-[10.88px] font-bold tracking-[1.088px] leading-[normal] min-h-[auto] min-w-[auto] outline-[3px] text-center no-underline border px-[9.28px] py-[4.8px] rounded-[7px] border-white/10 font-montserrat hover:text-emerald-500 hover:border-emerald-500 transition-colors"
            >
                RU
            </button> */}
            <button
                aria-label={open ? "Close menu" : "Open menu"}
                onClick={onToggle}
                className="items-center bg-white/5 caret-transparent flex text-[13.3333px] h-[42px] justify-center leading-[normal] min-h-[auto] min-w-[auto] outline-[3px] text-center no-underline w-[42px] border p-0 rounded-[10px] border-white/10 transition-colors hover:bg-white/10"
            >
                <div className="box-border caret-transparent gap-x-[5px] flex flex-col min-h-[auto] min-w-[auto] outline-[3px] gap-y-[5px] no-underline w-5">
                    {open ? (
                        <>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm rotate-45 translate-y-[7px] transition-transform"></span>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm opacity-0 transition-opacity"></span>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm -rotate-45 -translate-y-[7px] transition-transform"></span>
                        </>
                    ) : (
                        <>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm transition-transform"></span>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm transition-opacity"></span>
                            <span className="bg-white/80 block h-0.5 w-full rounded-sm transition-transform"></span>
                        </>
                    )}
                </div>
            </button>
        </div>
    );
};