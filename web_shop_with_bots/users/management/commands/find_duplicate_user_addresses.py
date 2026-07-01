from collections import defaultdict

from django.core.management.base import BaseCommand

from users.models import BaseProfile, UserAddress


def normalize_part(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def address_key(address: UserAddress) -> tuple[str, str, str | None]:
    return (
        (address.city or "").strip(),
        (address.address or "").strip(),
        normalize_part(address.flat),
    )


class Command(BaseCommand):
    help = (
        "Показывает клиентов, у которых есть дубли адресов "
        "в addresses (по city + address + flat)."
    )

    def handle(self, *args, **options):
        duplicate_clients = []
        total_clients_with_duplicates = 0

        profiles = (
            BaseProfile.objects
            .prefetch_related("addresses")
            .order_by("id")
        )

        for profile in profiles:
            addresses = list(profile.addresses.all())
            if len(addresses) < 2:
                continue

            grouped = defaultdict(list)
            for addr in addresses:
                grouped[address_key(addr)].append(addr)

            duplicates = {
                key: items
                for key, items in grouped.items()
                if len(items) > 1
            }

            if duplicates:
                total_clients_with_duplicates += 1
                duplicate_clients.append((profile, duplicates))

        self.stdout.write(
            self.style.SUCCESS(
                f"Клиентов с дублями адресов: {total_clients_with_duplicates}"
            )
        )

        if not duplicate_clients:
            return

        for profile, duplicates in duplicate_clients:
            self.stdout.write("")
            self.stdout.write(
                f"BaseProfile #{profile.id} | "
                f"{profile.first_name or ''} {profile.last_name or ''} | "
                f"{profile.phone or '-'} | {profile.email or '-'}"
            )

            for key, items in duplicates.items():
                city, address, flat = key
                ids = [item.id for item in items]
                self.stdout.write(
                    f"  DUPLICATE: city='{city}', address='{address}', flat='{flat}' "
                    f"-> ids={ids}, count={len(items)}"
                )
