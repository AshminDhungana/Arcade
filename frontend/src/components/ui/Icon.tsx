// frontend/src/components/ui/Icon.tsx
import { forwardRef, SVGAttributes } from 'react';
import type { LucideIcon } from 'lucide-react';
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
  InfoCircle,
  Check,
  X,
  Plus,
  Minus,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Menu,
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
  Print,
  Copy,
  Edit,
  Trash2,
  Archive,
  Folder,
  File,
  FileText,
  Image,
  Video,
  Music,
  Clock,
  Timer,
  Stopwatch,
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
  Desktop,
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
  Github,
  Gitlab,
  Bitbucket,
  Docker,
  Kubernetes,
  Aws,
  Azure,
  GoogleCloud,
  Vercel,
  Netlify,
  Railway,
  PlanetScale,
  Supabase,
  Firebase,
  MongoDB,
  Postgres,
  MySql,
  Redis,
  Elasticsearch,
  Kafka,
  RabbitMQ,
  GraphQL,
  Rest,
  Webhook,
  WebSocket,
  Api,
  Sdk,
  Cli,
  Gui,
  ApiKey,
  Token,
  Secret,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  LockKeyhole,
  UnlockKeyhole,
  Fingerprint,
  FaceId,
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
  TagMinus,
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
  Resize,
  Maximize,
  Minimize,
  Expand,
  Contract,
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
  MenuHorizontal,
  MenuVertical,
  MoreHorizontal,
  MoreVertical,
  DotsHorizontal,
  DotsVertical,
  Ellipsis,
  EllipsisHorizontal,
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
} from 'lucide-react';

// 1 — Icon name allow-list
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
  | 'InfoCircle'
  | 'Check'
  | 'X'
  | 'Plus'
  | 'Minus'
  | 'ChevronLeft'
  | 'ChevronRight'
  | 'ChevronUp'
  | 'ChevronDown'
  | 'Menu'
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
  | 'Print'
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
  | 'Stopwatch'
  | 'Calendar'
  | 'CalendarDays'
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
  | 'Desktop'
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
  | 'Github'
  | 'Gitlab'
  | 'Bitbucket'
  | 'Docker'
  | 'Kubernetes'
  | 'Aws'
  | 'Azure'
  | 'GoogleCloud'
  | 'Vercel'
  | 'Netlify'
  | 'Railway'
  | 'PlanetScale'
  | 'Supabase'
  | 'Firebase'
  | 'MongoDB'
  | 'Postgres'
  | 'MySql'
  | 'Redis'
  | 'Elasticsearch'
  | 'Kafka'
  | 'RabbitMQ'
  | 'GraphQL'
  | 'Rest'
  | 'Webhook'
  | 'WebSocket'
  | 'Api'
  | 'Sdk'
  | 'Cli'
  | 'Gui'
  | 'ApiKey'
  | 'Token'
  | 'Secret'
  | 'Shield'
  | 'ShieldCheck'
  | 'ShieldAlert'
  | 'ShieldOff'
  | 'LockKeyhole'
  | 'UnlockKeyhole'
  | 'Fingerprint'
  | 'FaceId'
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
  | 'TagMinus'
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
  | 'Resize'
  | 'Maximize'
  | 'Minimize'
  | 'Expand'
  | 'Contract'
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
  | 'MenuHorizontal'
  | 'MenuVertical'
  | 'MoreHorizontal'
  | 'MoreVertical'
  | 'DotsHorizontal'
  | 'DotsVertical'
  | 'Ellipsis'
  | 'EllipsisHorizontal'
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
  | 'BadgeQuestionMark';

// 2 — Icon size union (only allowed sizes)
export type IconSize = 16 | 20 | 24 | 28 | 32 | 40 | 48 | 56;

// 3 — Variant (stroke | fill)
export type IconVariant = 'stroke' | 'fill';

const sizeClassMap: Record<IconSize, string> = {
  16: 'h-4 w-4',
  20: 'h-5 w-5',
  24: 'h-6 w-6',
  28: 'h-7 w-7',
  32: 'h-8 w-8',
  40: 'h-10 w-10',
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
  InfoCircle,
  Check,
  X,
  Plus,
  Minus,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Menu,
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
  Print,
  Copy,
  Edit,
  Trash2,
  Archive,
  Folder,
  File,
  FileText,
  Image,
  Video,
  Music,
  Clock,
  Timer,
  Stopwatch,
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
  Desktop,
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
  Github,
  Gitlab,
  Bitbucket,
  Docker,
  Kubernetes,
  Aws,
  Azure,
  GoogleCloud,
  Vercel,
  Netlify,
  Railway,
  PlanetScale,
  Supabase,
  Firebase,
  MongoDB,
  Postgres,
  MySql,
  Redis,
  Elasticsearch,
  Kafka,
  RabbitMQ,
  GraphQL,
  Rest,
  Webhook,
  WebSocket,
  Api,
  Sdk,
  Cli,
  Gui,
  ApiKey,
  Token,
  Secret,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldOff,
  LockKeyhole,
  UnlockKeyhole,
  Fingerprint,
  FaceId,
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
  TagMinus,
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
  Resize,
  Maximize,
  Minimize,
  Expand,
  Contract,
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
  MenuHorizontal,
  MenuVertical,
  MoreHorizontal,
  MoreVertical,
  DotsHorizontal,
  DotsVertical,
  Ellipsis,
  EllipsisHorizontal,
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
};

// 5 — Icon component
interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, 'width' | 'height'> {
  name: IconName;
  size?: IconSize;
  variant?: IconVariant;
  className?: string;
  'aria-hidden'?: boolean;
}

export const Icon = forwardRef<SVGSVGElement, IconProps>(
  ({ name, size = 24, variant = 'stroke', className = '', 'aria-hidden': ariaHidden = true, ...props }, ref) => {
    const LucideIcon = iconMap[name];

    const variantProps =
      variant === 'fill'
        ? { fill: 'currentColor', stroke: 'none' }
        : { stroke: 'currentColor', fill: 'none', strokeWidth: 2 };

    return (
      <LucideIcon
        ref={ref}
        size={size}
        className={`${sizeClassMap[size]} ${className}`}
        role="img"
        aria-hidden={ariaHidden}
        {...variantProps}
        {...props}
      />
    );
  }
);

Icon.displayName = 'Icon';

// 6 — FaviconIcon SVG constant (stroke, 32×32)
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
  <rect x="2" y="3" width="20" height="14" rx="2" />
  <path d="M8 21h8" />
  <path d="M12 17v4" />
</svg>`;
