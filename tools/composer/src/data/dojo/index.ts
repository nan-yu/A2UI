// Real v0.8 scenarios from samples/agent/adk/ — verified working with the renderer
import restaurantBooking from './restaurant-booking.json';
import restaurantList from './restaurant-list.json';
import restaurantGrid from './restaurant-grid.json';
import restaurantConfirmation from './restaurant-confirmation.json';
import restaurantFinder from './restaurant-finder.json';
import bookingForm from './booking-form.json';
import contactCard from './contact-card.json';
import contactList from './contact-list.json';
import contactLookup from './contact-lookup.json';
import orgChart from './org-chart.json';
import floorPlan from './floor-plan.json';
import rizzchartsChart from './rizzcharts-chart.json';

export const scenarios = {
  'restaurant-booking': restaurantBooking,
  'restaurant-list': restaurantList,
  'restaurant-grid': restaurantGrid,
  'restaurant-confirmation': restaurantConfirmation,
  'restaurant-finder': restaurantFinder,
  'booking-form': bookingForm,
  'contact-card': contactCard,
  'contact-list': contactList,
  'contact-lookup': contactLookup,
  'org-chart': orgChart,
  'floor-plan': floorPlan,
  'rizzcharts-chart': rizzchartsChart,
};

export type ScenarioId = keyof typeof scenarios;
