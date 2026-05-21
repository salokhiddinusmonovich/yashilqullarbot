import { Link } from "react-router-dom";
import { LangSwitcher } from "./LangSwitcher";
import { useLang } from "../../../contexts/LanguageContext";

export const DesktopActions = () => {
    const { t } = useLang();

    return (
        <div className="items-center box-border caret-transparent gap-x-3 hidden shrink-0 min-h-0 min-w-0 outline-[3px] gap-y-3 no-underline md:flex md:min-h-[auto] md:min-w-[auto]">
            <LangSwitcher />
            <Link
                to="/registration"
                className="items-center bg-emerald-500 shadow-[rgba(255,102,0,0.3)_0px_4px_20px_0px] box-border caret-transparent gap-x-2 inline-flex text-[11.2px] font-bold justify-center tracking-[1.12px] leading-[17.92px] min-h-0 min-w-0 outline-[3px] relative gap-y-2 no-underline uppercase text-nowrap overflow-hidden px-[21.6px] py-[11.52px] rounded-lg font-montserrat md:flex md:min-h-[auto] md:min-w-[auto] md:px-4 md:py-2 hover:bg-emerald-600 hover:shadow-[rgba(255,102,0,0.45)_0px_8px_32px_0px] transition-all"
            >
                {t.navRegister}
            </Link>
        </div>
    );
};
