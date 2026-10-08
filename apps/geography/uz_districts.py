"""
O'zbekiston hududlari bo'yicha tumanlar va viloyatga bo'ysunuvchi shaharlar.

Kalit — `Region.name` bilan aynan bir xil. Toshkent viloyati tumanlari
chegara chizmasidagi (`src/data/uzbekistan.js`) nomlar bilan mos keladi.
Migrant formasida "chiqqan tumani / shahri" shu ro'yxatdan tanlanadi.
"""

UZ_DISTRICTS: dict[str, list[str]] = {
    "Qoraqalpog‘iston": [
        "Amudaryo", "Beruniy", "Bo‘zatov", "Chimboy", "Ellikqal’a", "Kegeyli",
        "Mo‘ynoq", "Nukus tumani", "Qanliko‘l", "Qo‘ng‘irot", "Qorao‘zak", "Shumanay",
        "Taxiatosh", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli",
        "Nukus shahri",
    ],
    "Andijon": [
        "Andijon tumani", "Asaka", "Baliqchi", "Bo‘ston", "Buloqboshi", "Izboskan",
        "Jalaquduq", "Marhamat", "Oltinko‘l", "Paxtaobod", "Qo‘rg‘ontepa", "Shahrixon",
        "Ulug‘nor", "Xo‘jaobod",
        "Andijon shahri", "Xonobod shahri",
    ],
    "Buxoro": [
        "Buxoro tumani", "G‘ijduvon", "Jondor", "Kogon tumani", "Olot", "Peshku",
        "Qorako‘l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent",
        "Buxoro shahri", "Kogon shahri",
    ],
    "Jizzax": [
        "Arnasoy", "Baxmal", "Do‘stlik", "Forish", "G‘allaorol", "Jizzax tumani",
        "Mirzacho‘l", "Paxtakor", "Yangiobod", "Zafarobod", "Zarbdor", "Zomin",
        "Jizzax shahri",
    ],
    "Qashqadaryo": [
        "Chiroqchi", "Dehqonobod", "G‘uzor", "Kasbi", "Kitob", "Koson", "Ko‘kdala",
        "Mirishkor", "Muborak", "Nishon", "Qamashi", "Qarshi tumani",
        "Shahrisabz tumani", "Yakkabog‘",
        "Qarshi shahri", "Shahrisabz shahri",
    ],
    "Navoiy": [
        "Karmana", "Konimex", "Navbahor", "Nurota", "Qiziltepa", "Tomdi",
        "Uchquduq", "Xatirchi",
        "Navoiy shahri", "Zarafshon shahri",
    ],
    "Namangan": [
        "Chortoq", "Chust", "Kosonsoy", "Mingbuloq", "Namangan tumani", "Norin",
        "Pop", "To‘raqo‘rg‘on", "Uchqo‘rg‘on", "Uychi", "Yangiqo‘rg‘on",
        "Namangan shahri",
    ],
    "Samarqand": [
        "Bulung‘ur", "Ishtixon", "Jomboy", "Kattaqo‘rg‘on tumani", "Narpay",
        "Nurobod", "Oqdaryo", "Pastdarg‘om", "Paxtachi", "Payariq", "Qo‘shrabot",
        "Samarqand tumani", "Toyloq", "Urgut",
        "Samarqand shahri", "Kattaqo‘rg‘on shahri",
    ],
    "Surxondaryo": [
        "Angor", "Bandixon", "Boysun", "Denov", "Jarqo‘rg‘on", "Muzrabot", "Oltinsoy",
        "Qiziriq", "Qumqo‘rg‘on", "Sariosiyo", "Sherobod", "Sho‘rchi", "Termiz tumani",
        "Uzun",
        "Termiz shahri",
    ],
    "Sirdaryo": [
        "Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod",
        "Sirdaryo tumani", "Xovos",
        "Guliston shahri", "Shirin shahri", "Yangiyer shahri",
    ],
    "Toshkent viloyati": [
        "Bekobod", "Bo‘ka", "Bo‘stonliq", "Chinoz", "Ohangaron", "Oqqo‘rg‘on",
        "O‘rta Chirchiq", "Parkent", "Piskent", "Qibray", "Quyi Chirchiq",
        "Toshkent tumani", "Yangiyo‘l", "Yuqori Chirchiq", "Zangiota",
        "Angren shahri", "Bekobod shahri", "Chirchiq shahri", "Nurafshon shahri",
        "Ohangaron shahri", "Olmaliq shahri", "Yangiyo‘l shahri",
    ],
    "Farg‘ona": [
        "Bag‘dod", "Beshariq", "Buvayda", "Dang‘ara", "Farg‘ona tumani", "Furqat",
        "Oltiariq", "Qo‘shtepa", "Quva", "Rishton", "So‘x", "Toshloq", "Uchko‘prik",
        "O‘zbekiston", "Yozyovon",
        "Farg‘ona shahri", "Marg‘ilon shahri", "Qo‘qon shahri", "Quvasoy shahri",
    ],
    "Xorazm": [
        "Bog‘ot", "Gurlan", "Hazorasp", "Qo‘shko‘pir", "Shovot", "Tuproqqal’a",
        "Urganch tumani", "Xiva tumani", "Xonqa", "Yangiariq", "Yangibozor",
        "Urganch shahri", "Xiva shahri",
    ],
    "Toshkent shahri": [
        "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug‘bek", "Olmazor", "Sergeli",
        "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yangihayot", "Yashnobod", "Yunusobod",
    ],
}


def ensure_districts(region_model, district_model) -> int:
    """
    Bazadagi har bir hududga ro'yxatdagi tumanlarni qo'shadi.

    Mavjud tuman (ko'rsatkichlari bilan) o'zgarmaydi, bazada yo'q hudud
    o'tkazib yuboriladi. Qo'shilgan tumanlar sonini qaytaradi.
    """
    created = 0
    for region in region_model.objects.filter(name__in=UZ_DISTRICTS):
        for name in UZ_DISTRICTS[region.name]:
            _, is_new = district_model.objects.get_or_create(region=region, name=name)
            created += is_new
    return created
