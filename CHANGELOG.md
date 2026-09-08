# История изменений

## 0.1.0-rc5 — 2026-09-08

- рабочая схема VLESS TLS Vision + Unix-Socket Decoy;
- API RemnaNode по умолчанию на TCP/2222 и ограничение IP панели;
- nginx только на `h1.sock`/`h2.sock`, права сокетов 0660;
- TLS 1.3, Let's Encrypt, временный TCP/80 и проверка продления;
- профиль `Vision-TLS`, AdGuard DoH и Comss DoH;
- systemd sandbox nginx, AppArmor, seccomp и no-new-privileges;
- TrafficGuard по выбору и автоматический выход из завершающего меню;
- русское оформление, контрольные этапы и расширенная диагностика;
- отдельное оформление проекта, лицензия MIT и документация профиля/Host.

