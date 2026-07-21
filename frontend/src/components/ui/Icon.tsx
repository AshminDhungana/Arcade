// frontend/src/components/ui/Icon.tsx
import { forwardRef, SVGAttributes } from 'react';
import type { LucideIcon } from 'lucide-react';
import { motion } from 'motion/react';
import { useReducedMotion } from 'motion/react';
import {
  GamepadDirectional,
  Monitor,
  Wifi,
  WifiOff,
  Power,
  CirclePause,
  CirclePlay,
  Square,
  Circle,
  Triangle,
  SquareX,
  CircleCheck,
  CircleX,
  TriangleAlert,
  Info,
  AlertCircle,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Menu,
  X,
  Settings,
  User,
  Users,
  Lock,
  Unlock,
  Key,
  Eye,
  EyeOff,
  Search,
  Filter,
  SortAsc,
  SortDesc,
  Download,
  Upload,
  Copy,
  Edit,
  Trash2,
  Archive,
  BarChart3,
  Folder,
  File,
  FileText,
  Image,
  Video,
  Music,
  Clock,
  Timer,
  Calendar,
  CalendarDays,
  MapPin,
  Navigation,
  Compass,
  Globe,
  Mail,
  MessageSquare,
  Send,
  Bell,
  BellOff,
  Volume2,
  VolumeX,
  Headphones,
  Mic,
  MicOff,
  Camera,
  CameraOff,
  Smartphone,
  Tablet,
  Laptop,
  Server,
  Database,
  HardDrive,
  Usb,
  Cpu,
  MemoryStick,
  MonitorCheck,
  MonitorOff,
  Keyboard,
  Mouse,
  Gamepad,
  Joystick,
  Gamepad2,
  Tv,
  Radio,
  Speaker,
  Headset,
  MousePointer,
  Touchpad,
  PenTool,
  Type,
  Code,
  Terminal,
  GitBranch,
  GitCommit,
  GitMerge,
  GitPullRequest,
  Webhook,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  LockKeyhole,
  UnlockKeyhole,
  Fingerprint,
  KeyRound,
  KeySquare,
  BadgePercent,
  BadgeCheck,
  BadgePlus,
  BadgeMinus,
  BadgeAlert,
  BadgeInfo,
  BadgeHelp,
  Award,
  Trophy,
  Medal,
  Crown,
  Star,
  StarHalf,
  Heart,
  HeartOff,
  ThumbsUp,
  ThumbsDown,
  Flag,
  FlagOff,
  Bookmark,
  BookmarkMinus,
  BookmarkPlus,
  Tag,
  TagPlus,
  Link,
  Link2,
  Unlink,
  Link2Off,
  ExternalLink,
  ArrowUpRight,
  ArrowDownLeft,
  ArrowUpLeft,
  ArrowDownRight,
  ArrowRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ArrowUpFromLine,
  ArrowDownToLine,
  ArrowLeftFromLine,
  ArrowRightToLine,
  RotateCw,
  RotateCcw,
  FlipHorizontal,
  FlipVertical,
  Move,
  MoveHorizontal,
  MoveVertical,
  MoveDiagonal,
  Maximize,
  Minimize,
  Expand,
  CornerUpLeft,
  CornerUpRight,
  CornerDownLeft,
  CornerDownRight,
  CornerLeftUp,
  CornerRightUp,
  CornerLeftDown,
  CornerRightDown,
  Grid,
  Grid2x2,
  Grid3x3,
  Layout,
  LayoutDashboard,
  LayoutGrid,
  LayoutList,
  LayoutTemplate,
  PanelLeft,
  PanelRight,
  PanelTop,
  PanelBottom,
  PanelTopOpen,
  PanelBottomOpen,
  PanelLeftOpen,
  PanelRightOpen,
  PanelTopClose,
  PanelBottomClose,
  PanelLeftClose,
  PanelRightClose,
  Sidebar,
  SidebarOpen,
  SidebarClose,
  MoreHorizontal,
  MoreVertical,
  Ellipsis,
  EllipsisVertical,
  Hexagon,
  Octagon,
  Pentagon,
  Diamond,
  HeartHandshake,
  Hand,
  Handshake,
  UserCheck,
  UserX,
  UserPlus,
  UserMinus,
  UserCog,
  UserSearch,
  UsersRound,
  Group,
  UserRound,
  UserRoundCheck,
  UserRoundX,
  UserRoundPlus,
  UserRoundMinus,
  UserRoundCog,
  UserRoundSearch,
  CircleUser,
  CircleUserRound,
  SquareUser,
  SquareUserRound,
  BadgeX,
  BadgeQuestionMark,
  HelpCircle,
} from 'lucide-react';

// 1 — Icon name allow-list (only icons that exist in lucide-react@1.21.0)
export type IconName =
  | 'GamepadDirectional'
  | 'Monitor'
  | 'Wifi'
  | 'WifiOff'
  | 'Power'
  | 'CirclePause'
  | 'CirclePlay'
  | 'Square'
  | 'Circle'
  | 'Triangle'
  | 'SquareX'
  | 'CircleCheck'
  | 'CircleX'
  | 'TriangleAlert'
  | 'Info'
  | 'AlertCircle'
  | 'CheckCircle'
  | 'XCircle'
  | 'AlertTriangle'
  | 'Check'
  | 'ChevronLeft'
  | 'ChevronRight'
  | 'ChevronUp'
  | 'ChevronDown'
  | 'Menu'
  | 'X'
  | 'Settings'
  | 'User'
  | 'Users'
  | 'Lock'
  | 'Unlock'
  | 'Key'
  | 'Eye'
  | 'EyeOff'
  | 'Search'
  | 'Filter'
  | 'SortAsc'
  | 'SortDesc'
  | 'Download'
  | 'Upload'
  | 'Copy'
  | 'Edit'
  | 'Trash2'
  | 'Archive'
  | 'Folder'
  | 'File'
  | 'FileText'
  | 'Image'
  | 'Video'
  | 'Music'
  | 'Clock'
  | 'Timer'
  | 'Calendar'
  | 'CalendarDays'
  | 'BarChart3'
  | 'MapPin'
  | 'Navigation'
  | 'Compass'
  | 'Globe'
  | 'Mail'
  | 'MessageSquare'
  | 'Send'
  | 'Bell'
  | 'BellOff'
  | 'Volume2'
  | 'VolumeX'
  | 'Headphones'
  | 'Mic'
  | 'MicOff'
  | 'Camera'
  | 'CameraOff'
  | 'Smartphone'
  | 'Tablet'
  | 'Laptop'
  | 'Server'
  | 'Database'
  | 'HardDrive'
  | 'Usb'
  | 'Cpu'
  | 'MemoryStick'
  | 'MonitorCheck'
  | 'MonitorOff'
  | 'Keyboard'
  | 'Mouse'
  | 'Gamepad'
  | 'Joystick'
  | 'Gamepad2'
  | 'Tv'
  | 'Radio'
  | 'Speaker'
  | 'Headset'
  | 'MousePointer'
  | 'Touchpad'
  | 'PenTool'
  | 'Type'
  | 'Code'
  | 'Terminal'
  | 'GitBranch'
  | 'GitCommit'
  | 'GitMerge'
  | 'GitPullRequest'
  | 'Webhook'
  | 'Shield'
  | 'ShieldCheck'
  | 'ShieldAlert'
  | 'ShieldOff'
  | 'LockKeyhole'
  | 'UnlockKeyhole'
  | 'Fingerprint'
  | 'KeyRound'
  | 'KeySquare'
  | 'BadgePercent'
  | 'BadgeCheck'
  | 'BadgePlus'
  | 'BadgeMinus'
  | 'BadgeAlert'
  | 'BadgeInfo'
  | 'BadgeHelp'
  | 'Award'
  | 'Trophy'
  | 'Medal'
  | 'Crown'
  | 'Star'
  | 'StarHalf'
  | 'Heart'
  | 'HeartOff'
  | 'ThumbsUp'
  | 'ThumbsDown'
  | 'Flag'
  | 'FlagOff'
  | 'Bookmark'
  | 'BookmarkMinus'
  | 'BookmarkPlus'
  | 'Tag'
  | 'TagPlus'
  | 'Link'
  | 'Link2'
  | 'Unlink'
  | 'Link2Off'
  | 'ExternalLink'
  | 'ArrowUpRight'
  | 'ArrowDownLeft'
  | 'ArrowUpLeft'
  | 'ArrowDownRight'
  | 'ArrowRight'
  | 'ArrowLeft'
  | 'ArrowUp'
  | 'ArrowDown'
  | 'ArrowUpFromLine'
  | 'ArrowDownToLine'
  | 'ArrowLeftFromLine'
  | 'ArrowRightToLine'
  | 'RotateCw'
  | 'RotateCcw'
  | 'FlipHorizontal'
  | 'FlipVertical'
  | 'Move'
  | 'MoveHorizontal'
  | 'MoveVertical'
  | 'MoveDiagonal'
  | 'Maximize'
  | 'Minimize'
  | 'Expand'
  | 'CornerUpLeft'
  | 'CornerUpRight'
  | 'CornerDownLeft'
  | 'CornerDownRight'
  | 'CornerLeftUp'
  | 'CornerRightUp'
  | 'CornerLeftDown'
  | 'CornerRightDown'
  | 'Grid'
  | 'Grid2x2'
  | 'Grid3x3'
  | 'Layout'
  | 'LayoutDashboard'
  | 'LayoutGrid'
  | 'LayoutList'
  | 'LayoutTemplate'
  | 'PanelLeft'
  | 'PanelRight'
  | 'PanelTop'
  | 'PanelBottom'
  | 'PanelTopOpen'
  | 'PanelBottomOpen'
  | 'PanelLeftOpen'
  | 'PanelRightOpen'
  | 'PanelTopClose'
  | 'PanelBottomClose'
  | 'PanelLeftClose'
  | 'PanelRightClose'
  | 'Sidebar'
  | 'SidebarOpen'
  | 'SidebarClose'
  | 'MoreHorizontal'
  | 'MoreVertical'
  | 'Ellipsis'
  | 'EllipsisVertical'
  | 'Hexagon'
  | 'Octagon'
  | 'Pentagon'
  | 'Diamond'
  | 'HeartHandshake'
  | 'Hand'
  | 'Handshake'
  | 'UserCheck'
  | 'UserX'
  | 'UserPlus'
  | 'UserMinus'
  | 'UserCog'
  | 'UserSearch'
  | 'UsersRound'
  | 'Group'
  | 'UserRound'
  | 'UserRoundCheck'
  | 'UserRoundX'
  | 'UserRoundPlus'
  | 'UserRoundMinus'
  | 'UserRoundCog'
  | 'UserRoundSearch'
  | 'CircleUser'
  | 'CircleUserRound'
  | 'SquareUser'
  | 'SquareUserRound'
  | 'BadgeX'
  | 'BadgeQuestionMark'
  | 'HelpCircle';

// 2 — Icon size union (only allowed sizes per spec)
export type IconSize = 14 | 16 | 20 | 24 | 28 | 32 | 48 | 56;

// 3 — Variant (stroke | fill)
export type IconVariant = 'stroke' | 'fill';

// 3b — Motion prop (none | entrance)
export type IconMotion = 'none' | 'entrance';

const sizeClassMap: Record<IconSize, string> = {
  14: 'h-3.5 w-3.5',
  16: 'h-4 w-4',
  20: 'h-5 w-5',
  24: 'h-6 w-6',
  28: 'h-7 w-7',
  32: 'h-8 w-8',
  48: 'h-12 w-12',
  56: 'h-14 w-14',
};

// 4 — IconName → Lucide component map (tree-shakeable via direct imports above)
const iconMap: Record<IconName, LucideIcon> = {
  GamepadDirectional,
  Monitor,
  Wifi,
  WifiOff,
  Power,
  CirclePause,
  CirclePlay,
  Square,
  Circle,
  Triangle,
  SquareX,
  CircleCheck,
  CircleX,
  TriangleAlert,
  Info,
  AlertCircle,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Menu,
  X,
  Settings,
  User,
  Users,
  Lock,
  Unlock,
  Key,
  Eye,
  EyeOff,
  Search,
  Filter,
  SortAsc,
  SortDesc,
  Download,
  Upload,
  Copy,
  Edit,
  Trash2,
  Archive,
  BarChart3,
  Folder,
  File,
  FileText,
  Image,
  Video,
  Music,
  Clock,
  Timer,
  Calendar,
  CalendarDays,
  MapPin,
  Navigation,
  Compass,
  Globe,
  Mail,
  MessageSquare,
  Send,
  Bell,
  BellOff,
  Volume2,
  VolumeX,
  Headphones,
  Mic,
  MicOff,
  Camera,
  CameraOff,
  Smartphone,
  Tablet,
  Laptop,
  Server,
  Database,
  HardDrive,
  Usb,
  Cpu,
  MemoryStick,
  MonitorCheck,
  MonitorOff,
  Keyboard,
  Mouse,
  Gamepad,
  Joystick,
  Gamepad2,
  Tv,
  Radio,
  Speaker,
  Headset,
  MousePointer,
  Touchpad,
  PenTool,
  Type,
  Code,
  Terminal,
  GitBranch,
  GitCommit,
  GitMerge,
  GitPullRequest,
  Webhook,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  LockKeyhole,
  UnlockKeyhole,
  Fingerprint,
  KeyRound,
  KeySquare,
  BadgePercent,
  BadgeCheck,
  BadgePlus,
  BadgeMinus,
  BadgeAlert,
  BadgeInfo,
  BadgeHelp,
  Award,
  Trophy,
  Medal,
  Crown,
  Star,
  StarHalf,
  Heart,
  HeartOff,
  ThumbsUp,
  ThumbsDown,
  Flag,
  FlagOff,
  Bookmark,
  BookmarkMinus,
  BookmarkPlus,
  Tag,
  TagPlus,
  Link,
  Link2,
  Unlink,
  Link2Off,
  ExternalLink,
  ArrowUpRight,
  ArrowDownLeft,
  ArrowUpLeft,
  ArrowDownRight,
  ArrowRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ArrowUpFromLine,
  ArrowDownToLine,
  ArrowLeftFromLine,
  ArrowRightToLine,
  RotateCw,
  RotateCcw,
  FlipHorizontal,
  FlipVertical,
  Move,
  MoveHorizontal,
  MoveVertical,
  MoveDiagonal,
  Maximize,
  Minimize,
  Expand,
  CornerUpLeft,
  CornerUpRight,
  CornerDownLeft,
  CornerDownRight,
  CornerLeftUp,
  CornerRightUp,
  CornerLeftDown,
  CornerRightDown,
  Grid,
  Grid2x2,
  Grid3x3,
  Layout,
  LayoutDashboard,
  LayoutGrid,
  LayoutList,
  LayoutTemplate,
  PanelLeft,
  PanelRight,
  PanelTop,
  PanelBottom,
  PanelTopOpen,
  PanelBottomOpen,
  PanelLeftOpen,
  PanelRightOpen,
  PanelTopClose,
  PanelBottomClose,
  PanelLeftClose,
  PanelRightClose,
  Sidebar,
  SidebarOpen,
  SidebarClose,
  MoreHorizontal,
  MoreVertical,
  Ellipsis,
  EllipsisVertical,
  Hexagon,
  Octagon,
  Pentagon,
  Diamond,
  HeartHandshake,
  Hand,
  Handshake,
  UserCheck,
  UserX,
  UserPlus,
  UserMinus,
  UserCog,
  UserSearch,
  UsersRound,
  Group,
  UserRound,
  UserRoundCheck,
  UserRoundX,
  UserRoundPlus,
  UserRoundMinus,
  UserRoundCog,
  UserRoundSearch,
  CircleUser,
  CircleUserRound,
  SquareUser,
  SquareUserRound,
  BadgeX,
  BadgeQuestionMark,
  HelpCircle,
};

// Internal animated wrapper component (no forwardRef to avoid issues with useReducedMotion + dynamic LucideIcon)
function AnimatedIconWrapper({
  LucideIcon,
  size,
  variantProps,
  className,
  ariaHidden,
  ...props
}: {
  LucideIcon: LucideIcon;
  size: IconSize;
  variantProps: { fill?: string; stroke?: string; strokeWidth?: number };
  className: string;
  ariaHidden: boolean;
  [key: string]: unknown;
}) {
  return (
    <motion.svg
      className={`${sizeClassMap[size]} ${className}`}
      role="img"
      aria-hidden={ariaHidden}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 260, damping: 24 }}
      {...props}
    >
      <LucideIcon size={size} {...variantProps} />
    </motion.svg>
  );
}

// 5 — Icon component
interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, 'width' | 'height'> {
  name: IconName;
  size?: IconSize;
  variant?: IconVariant;
  motion?: IconMotion;
  className?: string;
  'aria-hidden'?: boolean;
  // Accessibility props for when icon acts as button
  role?: string;
  tabIndex?: number;
  onClick?: MouseEventHandler<SVGSVGElement>;
  onKeyDown?: KeyboardEventHandler<SVGSVGElement>;
  'aria-label'?: string;
}

export const Icon = forwardRef<SVGSVGElement, IconProps>(
  (
    {
      name,
      size = 24,
      variant = 'stroke',
      motion = 'none',
      className = '',
      'aria-hidden': ariaHidden = true,
      role,
      tabIndex,
      onClick,
      onKeyDown,
      'aria-label': ariaLabel,
      ...props
    },
    ref,
  ) => {
    const LucideIcon = iconMap[name] ?? HelpCircle;
    const prefersReducedMotion = useReducedMotion();

    // Warn in dev for unknown icon names
    if (process.env.NODE_ENV !== 'production' && !iconMap[name]) {
      console.warn(
        `[Icon] Unknown icon name: "${name}". Falling back to "HelpCircle".`,
      );
    }

    const variantProps =
      variant === 'fill'
        ? { fill: 'currentColor', stroke: 'none' }
        : { stroke: 'currentColor', fill: 'none', strokeWidth: 2 };

    const shouldAnimate = motion === 'entrance' && size >= 32 && !prefersReducedMotion;

    // Build props for the Lucide icon (inner SVG)
    const lucideProps = {
      size,
      className: `${sizeClassMap[size]} ${className}`,
      role: role ?? 'img',
      'aria-hidden': role ? undefined : ariaHidden,
      'aria-label': ariaLabel,
      tabIndex,
      onClick,
      onKeyDown,
      ...variantProps,
      ...props,
    };

    if (shouldAnimate) {
      // Use separate component to avoid forwardRef + useReducedMotion + dynamic component issue
      return (
        <AnimatedIconWrapper
          LucideIcon={LucideIcon}
          size={size}
          variantProps={variantProps}
          className={className}
          ariaHidden={ariaHidden}
        />
      );
    }

    return <LucideIcon ref={ref} {...lucideProps} />;
  },
);

Icon.displayName = 'Icon';

// 6 — FaviconIcon SVG constant (GamepadDirectional, stroke, 32×32)
export const FaviconIcon = `<svg
  xmlns="http://www.w3.org/2000/svg"
  width="32"
  height="32"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <path d="M11.146 15.854a1.207 1.207 0 0 1 1.708 0l1.56 1.56A2 2 0 0 1 15 18.828V21a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-2.172a2 2 0 0 1 .586-1.414z" />
  <path d="M18.828 15a2 2 0 0 1-1.414-.586l-1.56-1.56a1.207 1.207 0 0 1 0-1.708l1.56-1.56A2 2 0 0 1 18.828 9H21a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1z" />
  <path d="M6.586 14.414A2 2 0 0 1 5.172 15H3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2.172a2 2 0 0 1 1.414.586l1.56 1.56a1.207 1.207 0 0 1 0 1.708z" />
  <path d="M9 3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2.172a2 2 0 0 1-.586 1.414l-1.56 1.56a1.207 1.207 0 0 1-1.708 0l-1.56-1.56A2 2 0 0 1 9 5.172z" />
</svg>`;
