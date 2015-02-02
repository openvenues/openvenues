import re
import urlparse

VCARD_TYPE = 'vcard'
SCHEMA_DOT_ORG_TYPE = 'schema.org'
RDFA_TYPE = 'rdfa'
ADDRESS_ELEMENT_TYPE = 'address'
GOOGLE_MAP_EMBED_TYPE = 'gmap'
GOOGLE_MAP_SHORTENED = 'gmap_short'
GEOTAG_TYPE = 'geotag'
OG_TAG_TYPE = 'og'
OG_BUSINESS_TAG_TYPE = 'og_business'
DATA_LATLON_TYPE = 'data_latlon'

HOPSTOP_MAP_TYPE = 'hopstop.map'
HOPSTOP_ROUTE_TYPE = 'hopstop.route'

MAPPOINT_EMBED_TYPE = 'mappoint.embed'

property_values = {
    'meta': 'content',
    'audio': 'src',
    'embed': 'src',
    'iframe': 'src',
    'img': 'src',
    'source': 'src',
    'video': 'src',
    'a': 'href',
    'area': 'href',
    'link': 'href',
    'object': 'data',
    'time': 'datetime',
}

br_regex = re.compile('<br[\s]*/?[\s]*>', re.I)


def br2nl(text):
    return br_regex.sub('\n', text)

latlon_splitter = re.compile('[\s]*;[\s]*')
latlon_comma_splitter = re.compile('[\s]*,[\s]*')

UNINTERESTING_PLACE_TYPES = set(s.lower() for s in [
    'Airport',
    'Airline',
    'AutoRepair',
    'ApartmentComplex',
    'Residence',
    'City',
    'SingleFamilyResidence',
    'Country',
    'SelfStorage',
    'RealEstateAgent',
    'State',
    'AdministrativeArea',
    'Continent',
])

PLACE_SCHEMA_TYPES = dict([(s.lower(), s) for s in [
    'Organization',
    'Corporation',
    'EducationalOrganization',
    'GovernmentOrganization',
    'NGO',
    'PerformingGroup',
    'SportsOrganization',
    'Place',
    'AdministrativeArea',
    'City',
    'Country',
    'State',
    'CivicStructure',
    'Airport',
    'Aquarium',
    'Beach',
    'BusStation',
    'BusStop',
    'Campground',
    'Cemetery',
    'Crematorium',
    'EventVenue',
    'FireStation',
    'GovernmentBuilding',
    'CityHall',
    'Courthouse',
    'DefenceEstablishment',
    'Embassy',
    'LegislativeBuilding',
    'Hospital',
    'MovieTheater',
    'Museum',
    'MusicVenue',
    'Park',
    'ParkingFacility',
    'PerformingArtsTheater',
    'PlaceOfWorship',
    'BuddhistTemple',
    'CatholicChurch',
    'Church',
    'HinduTemple',
    'Mosque',
    'Synagogue',
    'Playground',
    'PoliceStation',
    'RVPark',
    'StadiumOrArena',
    'SubwayStation',
    'TaxiStand',
    'TrainStation',
    'Zoo',
    'Landform',
    'BodyOfWater',
    'Canal',
    'LakeBodyOfWater',
    'OceanBodyOfWater',
    'Pond',
    'Reservoir',
    'RiverBodyOfWater',
    'SeaBodyOfWater',
    'Waterfall',
    'Continent',
    'Mountain',
    'Volcano',
    'LandmarksOrHistoricalBuildings',
    'LocalBusiness',
    'AnimalShelter',
    'AutomotiveBusiness',
    'AutoBodyShop',
    'AutoDealer',
    'AutoPartsStore',
    'AutoRental',
    'AutoRepair',
    'AutoWash',
    'GasStation',
    'MotorcycleDealer',
    'MotorcycleRepair',
    'ChildCare',
    'DryCleaningOrLaundry',
    'EmergencyService',
    'FireStation',
    'Hospital',
    'PoliceStation',
    'EmploymentAgency',
    'EntertainmentBusiness',
    'AdultEntertainment',
    'AmusementPark',
    'ArtGallery',
    'Casino',
    'ComedyClub',
    'MovieTheater',
    'NightClub',
    'FinancialService',
    'AccountingService',
    'AutomatedTeller',
    'BankOrCreditUnion',
    'InsuranceAgency',
    'FoodEstablishment',
    'Bakery',
    'BarOrPub',
    'Brewery',
    'CafeOrCoffeeShop',
    'FastFoodRestaurant',
    'IceCreamShop',
    'Restaurant',
    'Winery',
    'GovernmentOffice',
    'PostOffice',
    'HealthAndBeautyBusiness',
    'BeautySalon',
    'DaySpa',
    'HairSalon',
    'HealthClub',
    'NailSalon',
    'TattooParlor',
    'HomeAndConstructionBusiness',
    'Electrician',
    'GeneralContractor',
    'HVACBusiness',
    'HousePainter',
    'Locksmith',
    'MovingCompany',
    'Plumber',
    'RoofingContractor',
    'InternetCafe',
    'Library',
    'LodgingBusiness',
    'BedAndBreakfast',
    'Hostel',
    'Hotel',
    'Motel',
    'MedicalOrganization',
    'Dentist',
    'DiagnosticLab',
    'Hospital',
    'MedicalClinic',
    'Optician',
    'Pharmacy',
    'Physician',
    'VeterinaryCare',
    'ProfessionalService',
    'AccountingService',
    'Attorney',
    'Dentist',
    'Electrician',
    'GeneralContractor',
    'HousePainter',
    'Locksmith',
    'Notary',
    'Plumber',
    'RoofingContractor',
    'RadioStation',
    'RealEstateAgent',
    'RecyclingCenter',
    'SelfStorage',
    'ShoppingCenter',
    'SportsActivityLocation',
    'BowlingAlley',
    'ExerciseGym',
    'GolfCourse',
    'HealthClub',
    'PublicSwimmingPool',
    'SkiResort',
    'SportsClub',
    'StadiumOrArena',
    'TennisComplex',
    'Store',
    'AutoPartsStore',
    'BikeStore',
    'BookStore',
    'ClothingStore',
    'ComputerStore',
    'ConvenienceStore',
    'DepartmentStore',
    'ElectronicsStore',
    'Florist',
    'FurnitureStore',
    'GardenStore',
    'GroceryStore',
    'HardwareStore',
    'HobbyShop',
    'HomeGoodsStore',
    'JewelryStore',
    'LiquorStore',
    'MensClothingStore',
    'MobilePhoneStore',
    'MovieRentalStore',
    'MusicStore',
    'OfficeEquipmentStore',
    'OutletStore',
    'PawnShop',
    'PetStore',
    'ShoeStore',
    'SportingGoodsStore',
    'TireShop',
    'ToyStore',
    'WholesaleStore',
    'TelevisionStation',
    'TouristInformationCenter',
    'TravelAgency',
    'Residence',
    'ApartmentComplex',
    'GatedResidenceCommunity',
    'SingleFamilyResidence',
    'TouristAttraction',
]])
