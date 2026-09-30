import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faAppStore } from "@fortawesome/free-brands-svg-icons";
import {
  faLayerGroup,
  faChartSimple,
  faGear,
  faCreditCard,
  faPalette,
  faAt,
  faHashtag,
  faShop,
  faTicket,
  faRotateRight,
  faShield,
  faCloud,
  faBell,
  faGift,
  faDatabase,
  faBox,
  faHandshake,
  faLock,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

export type AppSidebarSection = {
  id: string;
  label: string;
  href: string;
  icon: IconDefinition;
};

export type AppSidebarGroup = {
  id: string;
  label: string;
  items: AppSidebarSection[];
  disabled?: boolean;
};

export const APP_SIDEBAR_BETA_MODE = true;

export function getAppSidebarGroups(base: string, opts?: { betaMode?: boolean }): AppSidebarGroup[] {
  const betaMode = opts?.betaMode ?? APP_SIDEBAR_BETA_MODE;
  return [
    {
      id: "aplicacao",
      label: "Aplicação",
      items: [
        { id: "overview", label: "Visão geral", href: `${base}/overview`, icon: faLayerGroup },
        { id: "restricted", label: "Restrito", href: `${base}/restricted`, icon: faTriangleExclamation   },
      ],
      disabled: false,
    },
    {
      id: "configuracoes",
      label: "Configurações",
      items: [
        { id: "incomes", label: "Rendimentos", href: `${base}/incomes`, icon: faChartSimple },
        { id: "customization", label: "Personalização", href: `${base}/config/customization`, icon: faPalette },
        { id: "roles", label: "Cargos", href: `${base}/config/roles`, icon: faAt },
        { id: "channels", label: "Canais", href: `${base}/config/channels`, icon: faHashtag },
        { id: "payments", label: "Pagamentos", href: `${base}/config/payments`, icon: faCreditCard },
        { id: "backup", label: "Backup", href: `${base}/backup`, icon: faDatabase },
        { id: "extensions", label: "Extensões", href: `${base}/extensions`, icon: faBox },
      ],
      disabled: betaMode,
    },
    {
      id: "sistemas",
      label: "Sistemas",
      items: [
        { id: "cloud", label: "Amethys Cloud", href: `${base}/cloud`, icon: faCloud },
        { id: "protections", label: "Proteções", href: `${base}/protections`, icon: faShield },
        { id: "automations", label: "Automações", href: `${base}/automations`, icon: faRotateRight },
        { id: "store", label: "Loja", href: `${base}/store`, icon: faShop },
        { id: "ticket", label: "Tickets", href: `${base}/ticket`, icon: faTicket },
        { id: "giveaway", label: "Sorteios", href: `${base}/giveaway`, icon: faGift },
      ],
      disabled: betaMode,
    },
  ];
}

