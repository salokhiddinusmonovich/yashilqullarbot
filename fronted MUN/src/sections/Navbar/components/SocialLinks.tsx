export const SocialLinks = () => {
    return (
        <div className="items-center box-border caret-transparent gap-x-2 flex shrink-0 min-h-[auto] min-w-[auto] outline-[3px] gap-y-2 no-underline md:gap-x-3 md:gap-y-3">
            <div className="bg-white/10 box-border caret-transparent h-[15px] min-h-[auto] min-w-[auto] outline-[3px] no-underline w-px md:h-5"></div>
            <div className="items-center box-border caret-transparent gap-x-[3.2px] flex min-h-[auto] min-w-[auto] outline-[3px] gap-y-[3.2px] no-underline md:gap-x-[4.8px] md:gap-y-[4.8px]">
                <a
                    href="https://www.instagram.com/tashkent.tech.mun/"
                    className="items-center box-border caret-transparent text-white/40 flex min-h-[auto] min-w-[auto] outline-[3px] no-underline p-1 hover:text-emerald-500 hover:border-emerald-500"
                >
                    <img
                        src="https://c.animaapp.com/mpbkoruiNSwSIb/assets/icon-1.svg"
                        alt="Icon"
                        className="box-border caret-transparent h-3.5 outline-[3px] no-underline align-baseline w-3.5 md:h-[15px] md:w-[15px]"
                    />
                </a>
                <a
                    href="https://t.me/tashkent_tech_mun"
                    className="items-center box-border caret-transparent text-white/40 flex min-h-[auto] min-w-[auto] outline-[3px] no-underline p-1 hover:text-emerald-500 hover:border-emerald-500"
                >
                    <img
                        src="https://c.animaapp.com/mpbkoruiNSwSIb/assets/icon-2.svg"
                        alt="Icon"
                        className="box-border caret-transparent h-3.5 outline-[3px] no-underline -translate-x-px translate-y-px align-baseline w-3.5 md:h-[15px] md:w-[15px]"
                    />
                </a>
            </div>
        </div>
    );
};